# -*- coding:utf-8 -*-

"""
utilizations for amr graph representaion

@author: Chuan Wang
@since: 2013-11-20
"""

from collections import defaultdict
import re

def trim_concepts(line):
    """
    quote all the string literals
    """
    pattern = re.compile('(:name\s*\(n / name\s*:op\d)\s*\(([^:)]+)\)\)')
    def quote(match):
        return match.group(1)+' "'+ match.group(2) + '")' 
    return pattern.sub(quote,line)


class StrLiteral(unicode):
    def __str__(self):
        return '"%s"' % "".join(self)

    def __repr__(self):
            return "".join(self)

class SpecialValue(str):
        pass

class Quantity(str):
        pass

class Polarity(str):
        pass

class Literal(str):
    def __str__(self):
        return "'%s" % "".join(self)

    def __repr__(self):
            return "".join(self)

class ListMap(defaultdict):
    '''
    Here we use Nathan Schneider (nschneid)'s nice ListMap implementation
    for bolinas.

    A  map that can contain several values for the same key.
    @author: Nathan Schneider (nschneid)
    @since: 2012-06-18

    >>> x = ListMap()
    >>> x.append('mykey', 3)
    >>> x.append('key2', 'val')
    >>> x.append('mykey', 8)
    >>> x
    defaultdict(<type 'list'>, {'key2': ['val'], 'mykey': [3, 8]})
    >>> x['mykey']
    3
    >>> x.getall('mykey')
    [3, 8]
    >>> x.items()
    [('key2', 'val'), ('mykey', 3), ('mykey', 8)]
    >>> x.itemsfor('mykey')
    [('mykey', 3), ('mykey', 8)]
    >>> x.replace('mykey', 0)
    >>> x
    defaultdict(<type 'list'>, {'key2': ['val'], 'mykey': [0]})
    '''
    
    def __init__(self, *args, **kwargs):
        defaultdict.__init__(self, list, *args, **kwargs)
    
    def __setitem__(self, k, v):
        if k in self:
            raise KeyError('Cannot assign to ListMap entry; use replace() or append()')
        return defaultdict.__setitem__(self, k, v)
    
    def __getitem__(self, k):
        '''Returns the *first* list entry for the key.'''
        return dict.__getitem__(self, k)[0]

    def getall(self, k):
        return dict.__getitem__(self, k)
        
    def items(self):
        return [(k,v) for k,vv in defaultdict.items(self) for v in vv]
    
    def values(self):
        return [v for k,v in self.items()]
    
    def itemsfor(self, k):
        return [(k,v) for v in self.getall(k)]
    
    def replace(self, k, v):
        defaultdict.__setitem__(self, k, [v])
        
    def append(self, k, v):
        defaultdict.__getitem__(self, k).append(v) 
    
    def remove(self, k, v):
        defaultdict.__getitem__(self, k).remove(v)        
        if not dict.__getitem__(self,k):
            del self[k]

    def __reduce__(self):
        t = defaultdict.__reduce__(self)
        return (t[0], ()) + t[2:]

    #def __str__(self):
    #    print map(lambda k: [k.encode("utf8"),','.join(map(lambda v:v.encode("utf8"),self[k]))],self)
    #     return str(map(lambda k: [k.encode("utf8"),','.join(map(lambda v:v,self[k]))],self))
# Lexer
class Lexer(object):
    """
    A simple generic lexer using Python re, that accepts a list of token
    definitions and ignores whitespaces.
    """
    def __init__(self, rules):
        """
        Initialize a new Lexer object using a set of lexical rules. 

        @type rules: A list of tuples (lextype, regex) where lextype is a 
        string identifying the lexical type of the token and regex is a python
        regular expression string. The order of tuples in the list matters.
        """
        self.tokenre = self.make_compiled_regex(rules)
        self.whitespacere = re.compile('[\s]*', re.MULTILINE)

    def make_compiled_regex(self, rules):
        regexstr =  '|'.join('(?P<%s>%s)' % (name, rule) for name, rule in rules)
        return re.compile(regexstr)

    def lex(self, s):
        """
        Perform the lexical scanning on a string and yield a (type, token, position)
        triple at a time. Whitespaces are skipped automatically.  
        This is a generator, so lexing is performed lazily. 
        """
        position = 0
        s = s.strip()
        while position < len(s):

            # Skip white spaces
            match = self.whitespacere.match(s, position)
            if match: 
                position = match.end()
    
            match = self.tokenre.match(s, position)
            if not match:
                raise LexerError, "Could not tokenize '%s'" % re.escape(s[position:])
            position = match.end()
            token = match.group(match.lastgroup)
            type = match.lastgroup
            yield type, token, position


class LexTypes:
    """
    Definitions of lexical types returned by the lexer.
    """
    LPAR = "LPAR" 
    RPAR = "RPAR"
    COMMA = "COMMA" 
    SLASH = "SLASH" 
    EDGELABEL = "EDGELABEL" 
    STRLITERAL = "STRLITERAL" 
    IDENTIFIER = "IDENTIFIER" 
    LITERAL =  "LITERAL"
    QUANTITY = "QUANTITY"


class Node():

    node_id = 0     #static counter, unique for each node
    mapping_table = {}  # old new index mapping table

    def __init__(self, trace, node_label, firsthit, leaf, depth):
        """
        initialize a node in the graph
        here a node keeps record of trace i.e. from where the node is reached (the edge label)
        so nodes with same other attributes may have different trace
        """
        self.trace = trace
        self.node_label = node_label
        self.firsthit = firsthit
        self.leaf = leaf
        self.depth = depth
        Node.node_id += 1                
        
    def __str__(self):
        return str((self.trace, self.node_label, self.depth))
        
    def __repr__(self):
        return str((self.trace, self.node_label, self.depth))


