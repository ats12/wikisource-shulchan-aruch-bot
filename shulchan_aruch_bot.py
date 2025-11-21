import pywikibot
from pywikibot import add_text
import wikitextparser as wtp
import re
import sys # for printing to stderr
from conversion_data import *
site = pywikibot.Site("he", "wikisource")

def get_completion_table(section):
    global site
    base_page_name = "ויקיטקסט:שולחן ערוך/מעקב אחרי קישורים לפרשנים/"
    completion_table = pywikibot.Page(site, base_page_name + section)
    return completion_table

def parse_completion_table(section):
    completion_table = get_completion_table(section)
    parsed = wtp.parse(completion_table.text)
    title_row = parsed.tables[0].data(row=0)
    commentersn = len(title_row)
    to_edit = []
    for table in parsed.tables:
        for row in table.data()[1:]:
            for i in range(commentersn):
                if row[i] == "":
                    section = row[0][2:-2]
                    to_edit.append((section, title_row[i]))
    return to_edit

# def create_completion_table(data):
#     table = """{| class="wikitable"
# ! הסעיף
# ! ט"ז
# ! מגן אברהם
# ! באר היטב
# ! שערי תשובה
# ! משנה ברורה
# ! ביאור הלכה
# ! כף החיים
# ! באר הגולה
# """
#     for row in data:
#         table += f"|-\n| "
#         for cell in row[:-1]:
#             table += cell
#             if cell != "": table += " "
#             table += "|| "
#         if row[-1] == "": table = table[:-1]
#         table += row[-1]
#         table += "\n"
#     table += "|}"
#     return table

def create_row(data):
    row = "| "
    for cell in data[:-1]:
        row += cell
        if cell != "": row += " "
        row += "|| "
    if data[-1] == "": row = row[:-1]
    row += data[-1]
    return row

def edit_completion_table(section_tuple, table_text, mark):
    parsed = wtp.parse(table_text)
    title_row = parsed.tables[0].data(row=0)
    for table in parsed.tables:
        table_data = table.data()[1:]
        for i, row in enumerate(table_data):
            if row[0][2:-2] == section_tuple[0]:
                new_row = row.copy()
                new_row[title_row.index(section_tuple[1])] = mark
                table_text = table_text.replace(create_row(row), create_row(new_row))
                return table_text

def update_completion_table(sections, mark):
    section = " ".join(sections[0][0].split()[2:5])
    completion_table = get_completion_table(" ".join(section.split()[:-1]))
    for section in sections:
        completion_table.text = edit_completion_table(section, completion_table.text)
    completion_table.save("עדכון פרשן שהושלם")

def construct_commenter(section, commenter):
    section = section[11:]
    page_format = commenter_page_format.get(commenter, commenter_page_format["default"])
    namespace = {
        "section": section,
        "commenter": commenter,
    }
    return eval(f'f"{page_format}"', {"__builtins__": {}}, namespace) #disabling builtins and only allowing access to the required variables for security of eval

def get_paragraphs(commenter_page):
    parsed_commenter = wtp.parse(commenter_page.text)
    paragraphs = [(template.get_arg("2"), template.get_arg("3").value) for template in parsed_commenter.templates if template.normal_name() == "משע"]
    return paragraphs

def edit_section(section_tuple: tuple):
    global site
    global commenter_shortcuts
    section = section_tuple[0]
    commenter = section_tuple[1]
    section_page = pywikibot.Page(site, section)
    commenter_page = pywikibot.Page(site, construct_commenter(section, commenter))
    if not commenter_page.exists(): return -1
    paragraphs = get_paragraphs(commenter_page)
    refs = [(paragraph[1], f"{{{{פרשע1|{commenter_shortcuts[commenter]}|{paragraph[0]}}}}}") for paragraph in paragraphs]
    if not refs: return -2
    not_done = []
    for ref in refs:
        if section_page.text.find(ref[1]): continue # if the reference is already found in the page, don't re-add it
        heading = re.search(heading_formats[commenter], ref[0]).group(1)
        insert_pos = re.search(heading, section_page.text)
        if insert_pos:
            insert_pos = insert_pos.start()
        else:
            not_done.append(ref[0])
        section_page.text = section_page.text[:insert_pos] + ref[1] + section_page.text[insert_pos:]
    if not_done == refs: return -3
    if not_done:
        message = f"\n=== הוספת הפניות ל{commenter} ===\nהוספו הפניות ל{commenter} באמצעות בוט. הסעיפים הקטנים הבאים לא הושלמו: {", ".join(not_done)}. ~~~~"
        section_page.save(f"הוספת הפניות חלקית, ראו פרטים נוספים בדף השיחה")
        discussion_page = pywikibot.Page(site, "שיחה:" + section)
        discussion_page.text += message
        discussion_page.save()
        return -4
    section_page.save(f"הוספת הפניות ל{commenter}.")
    return True


sections = ["אורח חיים", "יורה דעה", "אבן העזר", "חושן משפט"]
to_edit = []
for section in sections:
    to_edit += parse_completion_table(section)

done = []
partially_done = []
for section in to_edit:
    try:
        edit_status = edit_section(section)
    except Exception as error:
            print(error)

    match edit_status:
        case -1:
            print(f"דף המפרש {construct_commenter(section[0], section[1])} אינו קיים", file=sys.stderr)
        case -2:
            print(f"לא נמצאו תבניות {{{{משע}}}} בדף המפרש {construct_commenter(section[0], section[1])}", file=sys.stderr)
        case -3:
            print(f"הבוט לא הצליח לזהות את הדיבורים המתחילים של {section[1]} ב{section[0]}")
        case -4:
            partially_done.append(section)
            print(f"הפניות ל{section[1]} נוספו בהצלחה חלקית ל{section[0]}")
        case True:
            done.append(section)
            print(f"הפניות ל{section[1]} נוספו בהצלחה ל{section[0]}")
            break

update_completion_table(done, "{{v}}")
update_completion_table(partially_done, "{{v}}{{הערה|שם=השלמה חלקית בוט}}")
