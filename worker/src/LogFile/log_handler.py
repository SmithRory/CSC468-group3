import xmlschema as xs
from xml.etree.ElementTree import ElementTree
import os
import uuid

if __name__ == "__main__":
    schema = xs.XMLSchema('logfile.xsd')
    source = "testdata.json"
    f = open(source, "r")
    json_data = f.read() # this should later be a call to the database to retrieve logs as json\

    xml_data = xs.from_json(json_data,schema=schema)
    # write to XML file
    id = str(uuid.uuid1())
    filename = "log_" + id + ".xml" # to avoid replacing and loosing older log files
    ElementTree(xml_data).write(os.path.join(filename))

    # Uncomment to print the log file
#     print(xml_data)



