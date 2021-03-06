# -*- coding: utf-8 -*-
"""
Created on Mon Jun 01 08:37:36 2015

@author: vishwanathsindagi
"""

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json
from collections import defaultdict

"""
Your task is to wrangle the data and transform the shape of the data
into the model we mentioned earlier. The output should be a list of dictionaries
that look like this:

{
"id": "2406124091",
"type: "node",
"visible":"true",
"created": {
          "version":"2",
          "changeset":"17206049",
          "timestamp":"2013-08-03T16:43:42Z",
          "user":"linuxUser16",
          "uid":"1219059"
        },
"pos": [41.9757030, -87.6921867],
"address": {
          "housenumber": "5157",
          "postcode": "60625",
          "street": "North Lincoln Ave"
        },
"amenity": "restaurant",
"cuisine": "mexican",
"name": "La Cabana De Don Luis",
"phone": "1 (773)-271-5176"
}

You have to complete the function 'shape_element'.
We have provided a function that will parse the map file, and call the function with the element
as an argument. You should return a dictionary, containing the shaped data for that element.
We have also provided a way to save the data in a file, so that you could use
mongoimport later on to import the shaped data into MongoDB. 

Note that in this exercise we do not use the 'update street name' procedures
you worked on in the previous exercise. If you are using this code in your final
project, you are strongly encouraged to use the code from previous exercise to 
update the street names before you save them to JSON. 

In particular the following things should be done:
- you should process only 2 types of top level tags: "node" and "way"
- all attributes of "node" and "way" should be turned into regular key/value pairs, except:
    - attributes in the CREATED array should be added under a key "created"
    - attributes for latitude and longitude should be added to a "pos" array,
      for use in geospacial indexing. Make sure the values inside "pos" array are floats
      and not strings. 
- if second level tag "k" value contains problematic characters, it should be ignored
- if second level tag "k" value starts with "addr:", it should be added to a dictionary "address"
- if second level tag "k" value does not start with "addr:", but contains ":", you can process it
  same as any other tag.
- if there is a second ":" that separates the type/direction of a street,
  the tag should be ignored, for example:

<tag k="addr:housenumber" v="5158"/>
<tag k="addr:street" v="North Lincoln Avenue"/>
<tag k="addr:street:name" v="Lincoln"/>
<tag k="addr:street:prefix" v="North"/>
<tag k="addr:street:type" v="Avenue"/>
<tag k="amenity" v="pharmacy"/>

  should be turned into:

{...
"address": {
    "housenumber": 5158,
    "street": "North Lincoln Avenue"
}
"amenity": "pharmacy",
...
}

- for "way" specifically:

  <nd ref="305896090"/>
  <nd ref="1719825889"/>

should be turned into
"node_refs": ["305896090", "1719825889"]
"""

city_name1 = re.compile("bangalore", re.IGNORECASE)
city_name2 = re.compile("bengaluru", re.IGNORECASE)

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]

street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)


expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons"]

# UPDATE THIS VARIABLE
street_mapping = { "St": "Street",
            "St.": "Street",
            "Rd": "Road",
            "Rd." : "Road",
            "road" : "Road",
            "Ave" : "Avenue",
            "Ave." : "Avenue",
            "main" : "Main",            
            "cross" : "Cross"
            }

city_mapping = {
                "Bangalore":"Bengaluru",
                "bangalore":"Bengaluru",
                "BANGALORE":"Bengaluru",
                "bengaluru":"Bengaluru",
                "BENGALURU":"Bengaluru",
                }

def update_name(name, mapping):

    # YOUR CODE HERE
    names = name.split(' ')
    i = 0
    for word in names:       
       if mapping.has_key(word):
            newword = mapping[word]
            names[i] = newword
       i+=1
    name = ' '.join(names)
    return name


def shape_element(element):
    node = {}
    created = {}
    pos = {}
    address = {}
    node_refs = []
    if element.tag == "node" or element.tag == "way" :
        # YOUR CODE HERE
        for att in element.attrib:
            if att in CREATED:
                created[att] = element.attrib[att]
            elif att == "lat":
                pos["lat"] = float(element.attrib[att])
            elif att == "lon":
                pos["lon"] = float(element.attrib[att])
            else:
                node[att] = element.attrib[att]
            for subtag in element.iter():
               
                if subtag.tag == "tag":
                   
                    k = subtag.attrib["k"]
                    
                    if(problemchars.search(k) == None):
                        #print k
                        if k.find("addr:") == 0:
                            if k.find(":") == k.rfind(":"):
                                idx = k.find(":")
                                address_key = k[idx+1:]
                                value = subtag.attrib["v"]
                                if is_street_name(subtag):
                                    value = audit_street_name(value,street_mapping)
                                if is_city_name(subtag):
                                    value = audit_city_name(value, city_mapping)
                                if is_post_code(subtag):
                                    value = audit_post_code(value)                                
                                address[address_key] = value
                        else:
                            value = subtag.attrib["v"]
                            if is_phone(subtag):
                                
                                value = audit_phone(value)
                            node[k] = value
                if subtag.tag == "nd":                    
                    node_refs.append(subtag.attrib["ref"])
        if len(created) != 0:
            node["created"] = created
        if len(pos) != 0:
            node["pos"] = [pos["lat"],pos["lon"]]
        if len(address) != 0 :
            node["address"] = address
        if len(node_refs) != 0:
            node["node_refs"] = list(set( node_refs))
            
        node["type"] = element.tag
        return node
    else:
        return None

def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")

def is_city_name(elem):
    return (elem.attrib['k'] == "addr:city")
    
def is_post_code(elem):
    return (elem.attrib['k'] == "addr:postcode")

def is_phone(elem):
    return (elem.attrib['k'] == "phone")
    
def audit_street_name(value, mapping):
        
    values = value.split(' ')
    i = 0
    for word in values:       
       if mapping.has_key(word):
            newword = mapping[word]
            values[i] = newword
       i+=1
    value = ' '.join(values)  
    return value
    
def audit_city_name(value, mapping):
    if city_name1.search(value) or city_name2.search(value):
        values = value.split(' ')
        i = 0
        for word in values:       
            if mapping.has_key(word):
                newword = mapping[word]
                values[i] = newword
            i+=1
            value = ' '.join(values)  
    else:
        value = value + " ,Bengaluru"
        
    return value

def audit_post_code(value):
    value = value.replace(" ","")
    return value

def audit_phone(value):
    value = value.replace(" ","")
    value = value.replace("-","")
    value = value.replace(",",";")

def process_map(file_in, pretty = False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):           
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data

def test():
    # NOTE: if you are running this code on your computer, with a larger dataset, 
    # call the process_map procedure with pretty=False. The pretty=True option adds 
    # additional spaces to the output, making it significantly larger.
    data = process_map('sample.osm', False)
    pprint.pprint(data[-1])
    
   
if __name__ == "__main__":
    test()