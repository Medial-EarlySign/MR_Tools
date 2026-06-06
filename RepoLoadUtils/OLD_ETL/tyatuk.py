ALEF = 'א'
BAIS = 'ב'
GIMEL = 'ג'
DALET = 'ד'
HAY = 'ה'
VAV = 'ו'
ZAYIN = 'ז'
KHESS = 'ח'
TESS = 'ט'
YUD = 'י'
KHAF2 = 'ך'
KAF = 'כ'
LAMED = 'ל'
MEM2 = 'ם'
MEM = 'מ'
NUN2 = 'ן'
NUN = 'נ'
SAMEKH = 'ס'
AYIN = 'ע'
FAY2 = 'ף'
PAY = 'פ'
TSADI2 = 'ץ'
TSADI = 'צ'
KUF = 'ק'
RAISH = 'ר'
SHIN = 'ש'
TAF = 'ת'
BLANK = ' '
GERESH = "'"


def AtStart(i, text):
    return (i == 0) or (text[i - 1] == ' ')


def AtEnd(i, text):
    return (i == len(text) - 1) or (text[i + 1] == ' ')


def PrevChar(i, text):
    if AtStart(i, text):
        return ""
    return text[i - 1]


def NextChar(i, text):
    if AtEnd(i, text):
        return ""
    return text[i + 1]


def DisplayEnglish(text):

    yiddish = False
    ashkenazi = True
    sephardic = False
    englishText = ['']
    for i in range(0, len(text)):
        hebrewLetter = text[i]
        englishLetter = ''
        if hebrewLetter == ALEF:
            if NextChar(i, text) == VAV or NextChar(i, text) == YUD:
                continue
            else:
                englishLetter = 'A|O'
        elif hebrewLetter == BAIS:
            if AtStart(i, text) or yiddish:
                englishLetter = 'B'
            else:
                englishLetter = 'V|B'
        elif hebrewLetter == GIMEL:
            englishLetter = 'G'
        elif hebrewLetter == DALET:
            englishLetter = 'D'
        elif hebrewLetter == HAY:
            englishLetter = 'H'
        elif hebrewLetter == VAV:
            if NextChar(i, text) == VAV:
                if yiddish:
                    englishLetter = 'V'
                else:
                    englishLetter = 'W'
                i=+1
            elif yiddish:
                englishLetter = 'O|U'
            elif AtStart(i, text):
                englishLetter = 'V'
            elif AtStart(i - 1, text) and PrevChar(i, text) == ALEF:
                englishLetter = 'O|U|AV'
            else:
                englishLetter = 'O|U|V'
        elif hebrewLetter == ZAYIN:
            englishLetter = 'Z'
        elif hebrewLetter == KHESS:
            englishLetter = 'KH'
        elif hebrewLetter == TESS:
            englishLetter = 'T'
        elif hebrewLetter == YUD:
            if AtStart(i, text):
                if NextChar(i, text) == ALEF or NextChar(i, text) == AYIN:
                    englishLetter = 'Y'
                else:
                    englishLetter = 'YI'

            elif AtEnd(i, text):
                englishLetter = 'Y'
            elif PrevChar(i, text) == YUD:
                englishLetter = 'I'
            elif NextChar(i, text) == YUD:
                englishLetter = "E"
            else:
                englishLetter = 'I'
        elif hebrewLetter == KAF:
            if yiddish:
                englishLetter = 'KH'
            elif AtStart(i, text):
                englishLetter = 'K'
            else:
                englishLetter = 'KH|K'
        elif hebrewLetter == KHAF2:
            englishLetter = 'KH'
        elif hebrewLetter == LAMED:
            englishLetter = 'L'
        elif hebrewLetter == MEM:
            englishLetter = 'M'
        elif hebrewLetter == MEM2:
            englishLetter = 'M'
        elif hebrewLetter == NUN:
            englishLetter = 'N'
        elif hebrewLetter == NUN2:
            englishLetter = 'N'
        elif hebrewLetter == SAMEKH:
            englishLetter = 'S'
        elif hebrewLetter == AYIN:
            if yiddish:
                englishLetter = 'E'
            else:
                englishLetter = 'A'
        elif hebrewLetter == PAY:
            if AtStart(i, text):
                englishLetter = 'P|F'
            else:
                englishLetter = 'F|P'
        elif hebrewLetter == FAY2:
            englishLetter = 'F'
        elif hebrewLetter == TSADI:
            englishLetter = 'TZ'
        elif hebrewLetter == TSADI2:
            englishLetter = 'TZ'
        elif hebrewLetter == KUF:
            englishLetter = 'K'
        elif hebrewLetter == RAISH:
            englishLetter = 'R'
        elif hebrewLetter == SHIN:
            if yiddish:
                englishLetter = 'SH'
            else:
                englishLetter = 'SH|S'
        elif hebrewLetter == TAF:
                englishLetter = 'T'

        elif hebrewLetter == BLANK:
            englishLetter = ' '

        englishLetterArray = englishLetter.split('|')
        englishText = [x + y for x in englishText for y in englishLetterArray]

    return englishText


#heb = DisplayEnglish('קרדיולוגיה')
#print(heb)
