import xmlschema as xs
from xml.etree.ElementTree import ElementTree

# import os
# from json2xml import json2xml
# from json2xml.utils import readfromurl, readfromstring, readfromjson

import JsonToXML
import xml.etree.cElementTree as ET
import xml.dom.minidom


# if __name__ == "__main__":
#     schema = xs.XMLSchema('logfile.xsd')
#     source = "testdata.json"
#     f = open(source, "r")
#     json_data = f.read() # this should later be a call to the database to retrieve logs as json\
#
#     xml_data = xs.from_json(json_data,schema=schema)
#     # write to XML file
# #     id = str(uuid.uuid1())
#     filename = "log_" + ".xml" # to avoid replacing and loosing older log files
#     ElementTree(xml_data).write(os.path.join(filename))

#     data = readfromjson("testdata.json")
#     print(json2xml.Json2xml(data, attr_type=False).to_xml())

#     data = "[{\"userCommand\":[{\"timestamp\":\"1609459200000\",\"server\":\"CLT1\",\"transactionNum\":\"1\",\"command\":\"ADD\",\"username\":\"jiosesdo\",\"funds\":\"100.00\"},{\"timestamp\":\"1609459200000\",\"server\":\"CLT1\",\"transactionNum\":\"2\",\"command\":\"BUY\",\"username\":\"jiosesdo\",\"stockSymbol\":\"ABC\",\"funds\":\"100.00\"},{\"timestamp\":\"1609459200000\",\"server\":\"CLT2\",\"transactionNum\":\"3\",\"command\":\"BUY\",\"username\":\"skelsioe\",\"stockSymbol\":\"DEF\",\"funds\":\"1000.00\"},{\"timestamp\":\"1609459200000\",\"server\":\"CLT2\",\"transactionNum\":\"4\",\"command\":\"SELL\",\"username\":\"bob\",\"stockSymbol\":\"GHI\",\"funds\":\"1000.00\"}],\"accountTransaction\":[{\"timestamp\":\"1609459200000\",\"server\":\"CLT2\",\"transactionNum\":\"1\",\"action\":\"add\",\"username\":\"jiosesdo\",\"funds\":\"100.00\"},{\"timestamp\":\"1609459200000\",\"server\":\"CLT2\",\"transactionNum\":\"2\",\"action\":\"remove\",\"username\":\"jiosesdo\",\"funds\":\"100.00\"}],\"systemEvent\":{\"timestamp\":\"1609459200000\",\"server\":\"HSD1\",\"transactionNum\":\"2\",\"command\":\"BUY\",\"username\":\"jiosesdo\",\"stockSymbol\":\"ABC\",\"funds\":\"100.00\"},\"quoteServer\":{\"timestamp\":\"1609459200000\",\"server\":\"QSRV1\",\"transactionNum\":\"2\",\"quoteServerTime\":\"1167631203000\",\"username\":\"jiosesdo\",\"stockSymbol\":\"ABC\",\"price\":\"10.00\",\"cryptokey\":\"IRrR7UeTO35kSWUgG0QJKmB35sL27FKM7AVhP5qpjCgmWQeXFJs35g==\"},\"errorEvent\":{\"timestamp\":\"1609459200000\",\"server\":\"CLT2\",\"transactionNum\":\"4\",\"command\":\"SELL\",\"username\":\"bob\",\"stockSymbol\":\"GHI\",\"funds\":\"1000.00\",\"errorMessage\":\"Account bob does not exist\"}}]"
#
#     root = JsonToXML.fromText(data, rootName="log") # convert the file to XML and return the root node
#     xmlData = ET.tostring(root, encoding='utf8',method='xml').decode() # convert the XML data to string
#     dom = xml.dom.minidom.parseString(xmlData)
#     prettyXmlData = dom.toprettyxml() # properly format the string of XML data
#     print(prettyXmlData) # print the formatted XML data
#     ElementTree(xml_data).write(os.path.join(filename))


    # Uncomment to print the log file
#     print(xml_data)

# send json_data as a string of json values, can change if db returns as a file
# creates an xml log file in the LogFile folder

def convertLogFile(json_data : str, output_file : str):
#     root = JsonToXML.fromText(json_data, rootName="log")
#     xmlData = ET.tostring(root, encoding='utf8',method='xml').decode()
#     dom = xml.dom.minidom.parseString(xmlData)
#     prettyXmlData = dom.toprettyxml()
#     ElementTree(prettyXmlData).write(output_file)
    JsonToXML.fromTexttoFile(json_data, output_file, rootName="log")
