import pywikibot
import wikitextparser as wtp
import re
import sys # for printing to stderr
import csv
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

# unneeded function left for reference
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

def edit_completion_table(section, commenter, table_text, mark):
    parsed = wtp.parse(table_text)
    title_row = parsed.tables[0].data(row=0)
    for table in parsed.tables:
        table_data = table.data()[1:]
        for i, row in enumerate(table_data):
            if row[0][2:-2] == section:
                new_row = row.copy()
                new_row[title_row.index(commenter)] = mark
                table_text = table_text.replace(create_row(row), create_row(new_row))
                return table_text

def update_completion_table(sections, kind):
    section = " ".join(sections[0][0].split()[2:5])
    match kind:
        case 1:
            mark = "{{v}}"
        case 2:
            mark = "{{v}}{{הערה|שם=השלמה חלקית בוט}}"
    completion_table = get_completion_table(" ".join(section.split()[:-1]))
    for section, commenter in sections:
        completion_table.text = edit_completion_table(section, commenter, completion_table.text, mark)
    if kind == 2:
        comment = "{{הערות שוליים|הערות={{הערה|שם=השלמה חלקית בוט|הושלם באופן חלקי על ידי בוט, לפרטים נוספים ראו את דף השיחה של הסימן.}}}}" 
        if comment not in completion_table.text:
            completion_table.text += comment
        completion_table.save(f"עדכון השלמה חלקית של {commenter} {section.split()[-1]}")
        return
    completion_table.save(f"עדכון השלמת {commenter} {section.split()[-1]}")

def construct_commenter(section, commenter):
    section = section[11:]
    page_format = commenter_page_format.get(commenter, commenter_page_format["default"])
    namespace = {
        "section": section,
        "commenter": commenter,
    }
    return eval(f'f"{page_format}"', {"__builtins__": {}}, namespace) #disabling builtins and only allowing access to the required variables for security of eval

def get_paragraphs(commenter_page):
    templates = re.finditer(r"\{\{משע\|.*?\|(.*?)\|(.*?)\}\}", commenter_page.text)
    paragraphs = [template.group(1, 2) for template in templates]
    return paragraphs

def construct_references(section, commenter):
    global site
    global commenter_shortcuts
    section_page = pywikibot.Page(site, section)
    commenter_page = pywikibot.Page(site, construct_commenter(section, commenter))
    if not commenter_page.exists(): return None
    paragraphs = get_paragraphs(commenter_page)
    refs = [(paragraph[1], f"{{{{פרשע1|{commenter_shortcuts[commenter]}|{paragraph[0]}}}}}", paragraph[0]) for paragraph in paragraphs]
    return refs

def edit_section(section, commenter):
    refs = construct_references(section, commenter)
    if not refs: return -2
    not_done = []
    with open("text.orig", "w") as f:
        f.write(section_page.text)
    current_pos = section_page.find("}}") # so no references are entered inside the title
    for heading, ref, letter in refs:
        print("הפניה להוספה: ", ref)
        if ref in section_page.text:
            print("ההפניה כבר קיימת.")
            continue # if the reference is already found in the page, don't re-add it
        if commenter in heading_formats.keys():
            heading = re.search(heading_formats[commenter], heading) # so no references are entered inside the title
            if heading: heading = heading.group(1)
            else: continue
        else:
            return -5
        print(f"ד\"ה: {heading}")
        insert_pos = re.search(heading, section_page.text[current_pos:])
        if insert_pos:
            insert_pos = current_pos + insert_pos.start() # to insert references in order
            print("נקודת הכנסה: ", insert_pos)
        else:
            print(f"ד\"ה {heading} לא נמצא בסימן.")
            not_done.append(letter)
            continue
        current_pos = insert_pos
        section_page.text = section_page.text[:insert_pos] + ref + section_page.text[insert_pos:]
    with open("text.mod", "w") as f:
        f.write(section_page.text)
    if not_done == [ref[2] for ref in refs]: return -3
    if not_done:
        # message = f"\n=== הוספת הפניות ל{commenter} ===\nהוספו הפניות ל{commenter} באמצעות בוט. הסעיפים הקטנים הבאים לא הושלמו: {", ".join(not_done)}. ~~~~"
        section_page.save(f"הוספת הפניות חלקית ל{commenter}, ראו פרטים נוספים בדף השיחה.")
        with open("not_done.log", a) as f:
            f.write(f"{commenter} {section.split()[-2:]}: {", ".join(not_done)}")
        # discussion_page = pywikibot.Page(site, "שיחה:" + section)
        # discussion_page.text += message
        # discussion_page.save()
        return -4
    section_page.save(f"הוספת הפניות ל{commenter}.")
    return True

# creating the list of sections and commenters references should be added to
sections = ["אורח חיים", "יורה דעה", "אבן העזר", "חושן משפט"]
to_edit = []
for section in sections:
    to_edit += parse_completion_table(section)

# creating a table of the references to be added
ref_file = open("references.csv", "w")
writer = csv.writer(ref_file)
for section, commenter in to_edit:
    refs = construct_references(section, commenter)
    if refs:
        rows = [(section, commenter, heading, ref, letter) for heading, ref, letter in refs]
        writer.writerows(rows)

close(ref_file)

#the editing code, currently commented out so no accidents could happen
# done = []
# partially_done = []
# for section, commenter in to_edit:
#     print(section)
#     edit_status = edit_section(section, commenter)
#
#     match edit_status:
#         case -1:
#             print(f"דף המפרש {construct_commenter(section, commenter)} אינו קיים", file=sys.stderr)
#         case -2:
#             print(f"לא נמצאו תבניות {{{{משע}}}} בדף המפרש {construct_commenter(section, commenter)}", file=sys.stderr)
#         case -3:
#             print(f"הבוט לא הצליח לזהות את הדיבורים המתחילים של {commenter} ב{section}")
#         case -4:
#             partially_done.append((section, commenter))
#             print(f"הפניות ל{commenter} נוספו בהצלחה חלקית ל{section}")
#         case -5:
#             print(f"אין תבנית מתאימה לדיבור המתחיל של {commenter}")
#         case True:
#             done.append((section, commenter))
#             print(f"הפניות ל{commenter} נוספו בהצלחה ל{section}")
#     if len(done) + len(partially_done) == 10: break
#
# if done:
#     update_completion_table(done, 1)
# if partially_done:
#     update_completion_table(partially_done, 2)
