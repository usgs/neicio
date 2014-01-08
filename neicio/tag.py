#!/usr/bin/env python

from xml.dom import minidom
import copy
import datetime

TIMEFMT = '%Y-%m-%d %H:%M:%S'

class Tag(object):
    def __init__(self,name,attributes={},data=None,root=None,schema=None):
        if not isinstance(attributes,dict):
            raise Exception,'Attributes for Tag %s are of type %s, not dict!' % (name,type(attributes))
        self.data = data
        self.attributes = attributes
        self.name = name
        self.schema = schema
        self.children = []

    def addAttribute(self,key,value):
        self.attributes[key] = value
        
    def loadFromFile(self,xmlfile):
        xmlstr = open(xmlfile,'rt').read()
        return self.loadFromString(xmlstr)

    def loadFromString(self,xmlstr):
        dom = minidom.parseString(xmlstr)
        if len(dom.childNodes) > 1:
            raise Exception,'XML string has more than one root node!'
        root = dom.firstChild
        self.name = root.nodeName
        atts = root.attributes
        hasData = root.firstChild.nodeType == root.TEXT_NODE and len(root.firstChild.nodeValue.strip())
        if len(atts) and hasData:
            pass
            #raise Exception,'You can have child elements or tag data, but not both!'
        if len(atts):
            for item in atts.items():
                key = item[0]
                value = item[1]
                self.attributes[key] = value
        if hasData:
            self.data = root.firstChild.nodeValue.strip()
        for child in root.childNodes:
            if child.nodeType == child.ELEMENT_NODE:
                self.children.append(copy.deepcopy(self.convertNode(child)))


    def convertNode(self,child):
        name = child.nodeName
        atts = child.attributes
        c1 = child.firstChild is not None
        hasData = False
        if c1:
            c2 = child.firstChild.nodeType == child.TEXT_NODE
            c3 = len(child.firstChild.nodeValue.strip())
            hasData = c1 and c2 and c3

        if len(atts) and hasData:
            pass
            #raise Exception,'You can have child elements or tag data, but not both!'
        attributes = {}
        if len(atts):
            for item in atts.items():
                key = item[0]
                value = item[1]
                try:
                    value = float(value)
                except ValueError,msg:
                    try:
                        value = int(value)
                    except ValueError,msg:
                        pass
                #this may be a time field - let's assume it is and try to parse it
                if (isinstance(value,str) or isinstance(value,unicode)) and (key.lower().count('time') or key.lower().count('date')): 
                    try:
                        value = datetime.datetime.strptime(value,TIMEFMT)
                    except ValueError:
                        pass #oh, well, I guess it isn't
                    
                attributes[key] = value
        data = None
        if hasData:
            data = child.firstChild.nodeValue.strip()
        children = []
        for child2 in child.childNodes:
            if child2.nodeType == child2.ELEMENT_NODE:
                children.append(copy.deepcopy(self.convertNode(child2)))
        t = Tag(name,attributes,data)
        for child in children:
            t.addChild(child)
        return t

    def __repr__(self):
        fmt = '[%s: Attributes: "%s" Data: %s... %i children]'
        attstr = ' '.join(self.attributes.keys())
        repstr = fmt % (self.name,attstr,self.data,len(self.children))
        return repstr

    def getChildren(self,name):
        children = []
        for child in self.children:
            if child.name == name:
                children.append(child)
        return children

    def addChild(self,tag):
        if not isinstance(tag,Tag):
            raise Exception,'addChild only takes Tag objects as arguments'
        if self.data is not None:
            raise Exception,'You can have child elements or tag data, but not both!'
        self.children.append(tag)

    def deleteChildren(self,tagname):
        if not isinstance(tagname,str):
            raise Exception,'deleteChildren only takes string objects as arguments'
        numchildren = 0
        goodchildren = []
        for child in self.children:
            if child.name != tagname:
                goodchildren.append(copy.deepcopy(child))
            else:
                numchildren += 1
        
        self.children = goodchildren
        return numchildren

    def renderTag(self,ntabs):
        hasAttributes = bool(len(self.attributes))
        hasData = self.data is not None
        hasChildren = bool(len(self.children))

        linestr = '\t'*ntabs+'<%s ' % self.name
        if hasAttributes:
            attstr = ''
            for key,value in self.attributes.iteritems():
                if isinstance(value,datetime.datetime):
                    value = value.strftime(TIMEFMT)
                attstr = attstr + '%s="%s" ' % (key,str(value))
            linestr = linestr + attstr.strip()
        if hasData or hasChildren:
            if hasData:
                linestr = linestr.rstrip() + '>\n'
                linestr = linestr + '\t'*(ntabs+1) + self.data + '\n' + '\t'*ntabs + '</%s>\n' % self.name
            if hasChildren:
                linestr = linestr.rstrip() + '>\n'
                for child in self.children:
                    linestr = linestr + child.renderTag(ntabs+1)
                linestr = linestr + '\n' + '\t'*ntabs + '</%s>\n' % self.name
                #linestr = linestr + '\t'*ntabs + '</%s>\n' % self.name
        else:
            linestr = linestr + '/>\n'
        return linestr

    def renderToXML(self,filename=None,ntabs=0):
        xmlstr = '<?xml version="1.0" encoding="US-ASCII" standalone="yes"?>\n'
        xmlstr = xmlstr + self.renderTag(ntabs)
        xmlstr2 = ''
        for line in xmlstr.split('\n'):
            if len(line.strip()):
                xmlstr2 = xmlstr2 + line + '\n'
        if filename is not None:
            f = open(filename,'wt')
            f.write(xmlstr2)
            f.close()
        return xmlstr


if __name__ == '__main__':
    root = Tag('parent',attributes={'name':'fred','age':34})
    child1 = Tag('child1',attributes={'name':'pebbles','age':10})
    c2data = '''I am a child that likes to say "Bam!" a lot.  My parents think that I am difficult, but you should see what Pebbles likes to do!'''
    child2 = Tag('child2',attributes={'name':'bam-bam','age':11},data=c2data)
    root.addChild(child1)
    root.addChild(child2)
    print root.renderToXML()
    


    
                

