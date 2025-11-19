import pywikibot
from pywikibot import pagegenerators
from pywikibot import textlib
import wikitextparser as wtp
import re
site = pywikibot.Site("he", "wikisource")

commenter_shortcuts = {"משנה ברורה": "מב", "פתחי תשובה": "פת", "באר היטב": "בהט", "מגן אברהם": "מא", "ביאור הלכה": "בהל", "טורי זהב": "טז", "ט\"ז": "טז", "כף החיים": "כהח", "באר הגולה": "בהג", "פרי מגדים": "פרמג"}

def construct_commenter(section, commenter):
    section = section[11:]
    match commenter:
        case "שערי תשובה":
            return "שערי תשובה (מרגליות)/" + " ".join(section.split()[:-1]) + "/" + section.split()[-1]
        case "כף החיים":
            return "כף החיים/" + " ".join(section.split()[:-1]) + "/" + section.split()[-1]
        case "באר הגולה":
            return "באר הגולה (רבקש) על " + section
        case _:
            return commenter + " על " + section

def parse_completion_table(section):
    global site
    base_page_name = "ויקיטקסט:שולחן ערוך/מעקב אחרי קישורים לפרשנים/"
    completion_table = pywikibot.Page(site, base_page_name + section)
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

def get_paragraphs(commenter_page):
    parsed_commenter = wtp.parse(commenter_page.text)
    paragraphs = [(template.get_arg("2"), template.get_arg("3")) for template in parsed_commenter.templates if template.normal_name() == "משע"]
    return paragraphs

def edit_section(section_tuple: tuple):
    global site
    global commenter_shortcuts
    section = section_tuple[0]
    commenter = section_tuple[1]
    section_page = pywikibot.Page(site, section)
    commenter_page = pywikibot.Page(site, construct_commenter(section, commenter))
    if not commenter_page.exists(): return False
    paragraphs = get_paragraphs(commenter_page)
    print(paragraphs)
    refs = [f"{{{{פרשע1|{commenter_shortcuts[commenter]}|{paragraph[0]}}}}}" for paragraph in paragraphs]

sections = ["אורח חיים", "יורה דעה", "אבן העזר", "חושן משפט"]
to_edit = []
for section in sections:
    to_edit += parse_completion_table(section)
