


# Reformats the list of fortune cookies in FortuneCookies.txt into javascript array format
textFile = open("FortuneCookies.txt", "r")

text = textFile.read()

inputArray = text.split("\n")
resultArray = []

for line in inputArray:
    line = line.replace('"', '\\"')
    resultArray.append("\"" + line + "\", ")

resultFile = open("FortuneCookiesArray.txt", "w")
for line in resultArray:
    resultFile.write(line)