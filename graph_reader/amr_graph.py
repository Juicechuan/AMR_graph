# -*- coding:utf-8 -*-

'''
A hypergraph representation for amr.

@author: Chuan Wang
@since: 2013-11-20
'''
from collections import defaultdict
from util import *
import re,sys

# Error definitions
class LexerError(Exception):
    pass
class ParserError(Exception):
    pass

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
    
    def __str__(self):
        return str((self.trace, self.node_label, self.depth))
        
    def __repr__(self):
        return str((self.trace, self.node_label, self.depth))

class AMR(defaultdict):
    """
    An abstract meaning representation.
    Basic idea is based on bolinas' hypergraph for amr.
    
    Here one AMR is a rooted, directed, acyclic graph.
    We also use the edge-label style in bolinas.
    """
    def __init__(self,*args, **kwargs):

        defaultdict.__init__(self,ListMap,*args,**kwargs)
        self.roots = []
        self.external_nodes = {}

        # attributes to be added
        self.node_to_concepts = {}

    @classmethod
    def parse_string(cls,amr_string):
        """
        Parse a Pennman style string representation for amr and return an AMR 
        
        >>>x = AMR.parse_string("(a / and :op1(恶化 :ARG0(它) :ARG1(模式 :mod(开发)) :time (已 经)) :op2(堵塞 :ARG0(它) :ARG1(交通 :mod(局部)) :location(a / around :op1(出口)))))")
        >>>
        .
        """

        def make_compiled_regex(rules):
            regexstr =  '|'.join('(?P<%s>%s)' % (name, rule) for name, rule in rules)
            return re.compile(regexstr)

        PNODE = 1
        CNODE = 2
        EDGE = 3
        
        amr = cls()
        stack = []
        state = 0

        lex_rules = [
            ("LPAR", '\('),
            ("RPAR",'\)'),
            ("COMMA",','), 
            ("SLASH",'/'),
            ("EDGELABEL",":[^\s()]+"),
            ("STRLITERAL",'"[^"]+"'),
            ("LITERAL","'[^\s(),]+"),
            ("IDENTIFIER","[^\s()]+"), #no blank within characters
            ("QUANTITY","[0-9][0-9Ee^+\-\.,:]*"),
        ] 
        
        token_re = make_compiled_regex(lex_rules)
        #lexer = Lexer(lex_rules)
        
        for match in token_re.finditer(amr_string):
            token = match.group()
            type = match.lastgroup

            #print token.strip(),type
            if state == 0:
                if type == "LPAR":
                    state = 1
                else: raise ParserError, "Unexpected token %s"%(token)

            elif state == 1:
                if type == "IDENTIFIER":
                    stack.append((PNODE,token.strip(),None))
                    state = 2
                else: raise ParserError , "Unexpected token %s"%(token)

            elif state == 2:
                if type == "SLASH":
                    state = 3
                elif type == "EDGELABEL":
                    stack.append((EDGE,token[1:]))
                    state = 5
                elif type == "RPAR":
                    forgetme, parentnodelabel, parentconcept = stack.pop()
                    assert forgetme == PNODE
                    foo = amr[parentnodelabel]
                    if stack:
                        stack.append((CNODE,parentnodelabel,parentconcept))
                        state = 6
                    else:
                        amr.roots.append(parentnodelabel)
                        state = 0
                    
                else: raise ParserError, "Unexpected token %s"%(token)

            elif state == 3:
                if type == "IDENTIFIER":
                    assert stack[-1][0] == PNODE
                    nodelabel = stack.pop()[1]
                    stack.append((PNODE,nodelabel,token))
                    state = 4
                else: raise ParserError, "Unexpected token %s"%(token)
            
            elif state == 4:
                if type == "EDGELABEL":
                    stack.append((EDGE,token[1:]))
                    state = 5
                elif type == "RPAR":
                    forgetme, parentnodelabel, parentconcept = stack.pop()
                    assert forgetme == PNODE
                    foo = amr[parentnodelabel] # add only the node
                    amr.node_to_concepts[parentnodelabel] = parentconcept
                    
                    if stack:
                        stack.append((CNODE,parentnodelabel,parentconcept))
                        state = 6
                    else:
                        amr.roots.append(parentnodelabel)
                        state = 0
                else: raise ParserError, "Unexpected token %s"%(token)
                
            elif state == 5:
                if type == "LPAR":
                    state = 1
                elif type == "QUANTITY":
                    stack.append((CNODE,token,None))
                    state = 6
                elif type == "STRLITERAL":
                    stack.append((CNODE,token[1:-1],None))
                    state = 6
                elif type == "LITERAL":
                    stack.append((CNODE,token[1:],None))
                    state = 6
                elif type == "IDENTIFIER":
                    stack.append((CNODE,token,None))
                    state = 6
                elif type == "EDGELABEL": #Unary edge
                    stack.append((CNODE,None,None)) 
                    stack.append((EDGE,token[1:]))
                    state = 5
                
                elif type == "RPAR":
                    stack.append((CNODE,None,None))
                    edges = []
                    
                    while stack[-1][0] != PNODE:
                        children = []
                        #one edge may have multiple children/tail nodes
                        while stack[-1][0] == CNODE:
                            forgetme, childnodelabel, childconcept = stack.pop()
                            children.append((childnodelabel,childconcept))
                        
                        assert stack[-1][0] == EDGE
                        forgetme, edgelabel = stack.pop()
                        edges.append((edgelabel,children))
                    
                    forgetme,parentnodelabel,parentconcept = stack.pop()
                    amr.node_to_concepts[parentnodelabel] = parentconcept
                    for edgelabel,children in edges:
                        hypertarget = []
                        for node, concept in children:
                            if node is not None:
                                if concept and (not node in amr.node_to_concepts or concept is not None):
                                    amr.node_to_concepts[node] = concept
                            hypertarget.append(node)
                        hyperchild = tuple(hypertarget)
                        amr._add_triple(parentnodelabel,edgelabel,hyperchild)
                    
                    if stack: #we have done with current level
                        state = 6
                        stack.append((CNODE, parentnodelabel, parentconcept))
                    else: #we have done with this subgraph
                        state = 0
                        amr.roots.append(parentlabel)

            elif state == 6:
                if type == "RPAR":
                    
                    edges = []
                    while stack[-1][0] != PNODE:
                        children = []
                        #one edge may have multiple children/tail nodes
                        while stack[-1][0] == CNODE:
                            forgetme, childnodelabel, childconcept = stack.pop()
                            children.append((childnodelabel,childconcept))
                        
                        assert stack[-1][0] == EDGE
                        forgetme, edgelabel = stack.pop()
                        edges.append((edgelabel,children))
                    
                    forgetme,parentnodelabel,parentconcept = stack.pop()
                    amr.node_to_concepts[parentnodelabel] = parentconcept
                    for edgelabel,children in edges:
                        hypertarget = []
                        for node, concept in children:
                            if node is not None:
                                if concept and (not node in amr.node_to_concepts or concept is not None):
                                    amr.node_to_concepts[node] = concept
                            hypertarget.append(node)
                        hyperchild = tuple(hypertarget)
                        amr._add_triple(parentnodelabel,edgelabel,hyperchild)
                    
                    if stack: #we have done with current level
                        state = 6
                        stack.append((CNODE, parentnodelabel, parentconcept))
                    else: #we have done with this subgraph
                        state = 0
                        amr.roots.append(parentnodelabel)
                elif type == "COMMA": # to seperate multiple children/tails 
                    state = 7
                elif type == "EDGELABEL":
                    stack.append((EDGE,token[1:]))
                    state = 5
                else: raise ParserError, "Unexpected token %s"%(token)

            elif state == 7:
                if type == "IDENTIFIER":
                    stack.append((CNODE, token, None)) # another children
                    state = 6
                elif typpe == "LPAR":
                    state = 1
                else: raise ParserError, "Unexpected token %s"%(token)

        return amr

    def _add_triple(self, parent, relation, child, warn=sys.stderr):
        """                                                                                         
        Add a (parent, relation, child) triple to the DAG.                                          
        """
        if type(child) is not tuple:
            child = (child,)
        if parent in child:
            #raise Exception('self edge!')                                                          
            #sys.stderr.write("WARNING: Self-edge (%s, %s, %s).\n" % (parent, relation, child))     
            if warn: warn.write("WARNING: Self-edge (%s, %s, %s).\n" % (parent, relation, child))
            #raise ValueError, "Cannot add self-edge (%s, %s, %s)." % (parent, relation, child)     
        for c in child:
            x = self[c]
            for rel, test in self[c].items():
                if parent in test:
                   if warn: warn.write("WARNING: (%s, %s, %s) produces a cycle with (%s, %s, %s)\n" % (parent, relation, child, c, rel, test))
                    #raise ValueError,"(%s, %s, %s) would produce a cycle with (%s, %s, %s)" % (parent, relation, child, c, rel, test)                     

        self[parent].append(relation, child)                
    
    def dfs(self):
        """
        depth first search for the graph
        return dfs ordered nodes and edges
        """
        visited_nodes = set()
        visited_edges = set()
        sequences = []

        #import pdb
        #pdb.set_trace()
        
        #multi roots graph
        for r in self.roots:

            stack = [((r,),None,0)] # record the node, incoming edge and depth
            
            all_nodes = []
            while stack:
                next,rel,depth = stack.pop()
                for n in next:
                    firsthit = not n in visited_nodes
                    leaf = False if self[n] else True
                
                    node = Node(rel, n, firsthit, leaf, depth)
                    all_nodes.append(node)
                    if n in visited_nodes:
                        continue

                    visited_nodes.add(n)
                    for rel, child in reversed(self[n].items()):
                        #print rel,child
                        if not (n, rel, child) in visited_edges:
                            if child in visited_nodes:
                                stack.append((child,rel,depth+1))
                            else:
                                visited_edges.add((n,rel,child))
                                stack.append((child,rel,depth+1))
                                
            sequences.append(all_nodes)
        
        return sequences
            
    def to_amr_string(self):
        
        amr_string = ""
        
        scan_order = self.dfs()
        for seq in scan_order:
            #always begin with root
            assert seq[0].trace == None
            dep_rec = 0
            for node in seq:
                if node.trace == None:
                    if node.firsthit and node.node_label in self.node_to_concepts:
                        amr_string += "(%s / %s"%(node.node_label,self.node_to_concepts[node.node_label])
                    else:
                        amr_string += "(%s"%(node.node_label)
                else:
                    if node.depth >= dep_rec:
                            dep_rec = node.depth
                    else:
                        amr_string += "%s"%((dep_rec-node.depth)*')')
                        dep_rec = node.depth

                    if not node.leaf:
                        if node.firsthit and node.node_label in self.node_to_concepts:
                            amr_string += "\n%s:%s (%s / %s"%(node.depth*"\t",node.trace,node.node_label,self.node_to_concepts[node.node_label])
                        else:
                            amr_string += "\n%s:%s (%s"%(node.depth*"\t",node.trace,node.node_label)
                           
                    else:
                        if node.firsthit and node.node_label in self.node_to_concepts:
                            amr_string += "\n%s:%s (%s / %s)"%(node.depth*"\t",node.trace,node.node_label,self.node_to_concepts[node.node_label])
                        else:
                            amr_string += "\n%s:%s %s"%(node.depth*"\t",node.trace,node.node_label)

            if dep_rec != 0:
                amr_string += "%s"%((dep_rec)*')')

        return amr_string

if __name__ == "__main__":
    s = '''(a / and :op1(恶化 :ARG0(它) :ARG1(模式 :mod(开发)) :time (已经)) :op2(t / 堵塞 :ARG0(它) :ARG1(交通 :mod(局部)) :location(a1 / around :op1(出口))))'''
    s1 = '''(a  /  and :op1 (c  /  change-01 :ARG0 (i  /  it) :ARG1 (p  /  pattern :mod (d  /  develop-02)) :ARG2 (b  / bad :degree (m  /  more))) :op2 (c2  /  cause-01 :ARG0 i :ARG1 (c3  /  congest-01 :ARG1 (a2  /  around :op1 (e  /  exit :poss i)) :ARG2 (t  /  traffic) :ARG1-of (l2  /  localize-01))) :time (a3  /  already))'''
    s = s.decode('utf8')
    #import pdb 
    #pdb.set_trace()
    amr_ch = AMR.parse_string(s)
    amr_en = AMR.parse_string(s1)
    
    print str(amr_en)
    #print amr_en.dfs()
    print amr_en.to_amr_string()
    print str(amr_ch)
    #print amr_ch.dfs()
    print amr_ch.to_amr_string()
