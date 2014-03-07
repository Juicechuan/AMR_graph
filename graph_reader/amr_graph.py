#!/usr/bin/python
# -*- coding:utf-8 -*-

'''
A hypergraph representation for amr.

@author: Chuan Wang
@since: 2013-11-20
'''
from collections import defaultdict
from util import *
import re,sys
from optparse import OptionParser

# Error definitions
class LexerError(Exception):
    pass
class ParserError(Exception):
    pass

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
        node_idx = 0; # sequential new node index
        mapping_table = {};  # old new index mapping table

        lex_rules = [
            ("LPAR", '\('),
            ("RPAR",'\)'),
            ("COMMA",','), 
            ("SLASH",'/'),
            ("EDGELABEL",":[^\s()]+"),
            ("STRLITERAL",u'"[^"]+"|\u201c[^\u201d]+\u201d'),
            ("LITERAL","'[^\s(),]+"),
            ("QUANTITY","[0-9][0-9Ee^+\-\.,:]*"),
            ("IDENTIFIER","[^\s()]+"), #no blank within characters
            ("POLARITY","\s\-\s")
        ] 
        
        token_re = make_compiled_regex(lex_rules)
        #lexer = Lexer(lex_rules)

        for match in token_re.finditer(amr_string):
            token = match.group()
            type = match.lastgroup
            
            #if type == "STRLITERAL":
            #    import pdb
            #    pdb.set_trace()

            #print token.strip(),type
            if state == 0:
                if type == "LPAR":
                    state = 1
                else: raise ParserError, "Unexpected token %s"%(token)

            elif state == 1:
                if type == "IDENTIFIER":
                    stack.append((PNODE,token.strip(),None))
                    state = 2
                elif type == "QUANTITY":
                    stack.append((PNODE,Quantity(token.strip()),None))
                    state = 2
                elif type == "STRLITERAL":
                    stack.append((PNODE,StrLiteral(token.strip()),None))
                    state = 2
                else: raise ParserError , "Unexpected token %s"%(token.encode('utf8'))

            elif state == 2:
                if type == "SLASH":
                    state = 3
                elif type == "EDGELABEL":
                    stack.append((EDGE,token[1:]))
                    state = 5
                elif type == "RPAR":
                    forgetme, parentnodelabel, parentconcept = stack.pop()
                    assert forgetme == PNODE
                    assert parentconcept == None
                    
                    if parentnodelabel in mapping_table:
                        parentnodelabel = mapping_table[parentnodelabel]
                    else:
                        parentconcept = parentnodelabel
                        parentnodelabel = node_idx 
                        amr.node_to_concepts[parentnodelabel] = parentconcept
                        node_idx += 1

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
                    print state,parentnodelabel,parentconcept
                    if parentconcept is not None:
                        amr.node_to_concepts[parentnodelabel] = parentconcept
                    
                    if stack:
                        stack.append((CNODE,parentnodelabel,parentconcept))
                        state = 6
                    else:
                        amr.roots.append(parentnodelabel)
                        state = 0
                else: raise ParserError, "Unexpected token %s"%(token.encode('utf8'))
                
            elif state == 5:
                if type == "LPAR":
                    state = 1
                elif type == "QUANTITY":
                    stack.append((CNODE,Quantity(token),None))
                    state = 6
                elif type == "STRLITERAL":
                    stack.append((CNODE,StrLiteral(token[1:-1]),None))
                    state = 6
                elif type == "LITERAL":
                    stack.append((CNODE,token[1:],None))
                    state = 6
                elif type == "POLARITY":
                    stack.append((CNODE,Polarity(token.strip()),None))
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
                    print state,parentnodelabel,parentconcept

                    #check for annotation error
                    if parentnodelabel in amr.node_to_concepts.keys(): 
                        #concept has been defined by the children, 
                        #then they must have different concepts, otherwise the children's concepts should be None
                        #(coreference)
                        if amr.node_to_concepts[parentnodelabel] == parentconcept:
                            sys.stderr.write("Wrong annotation format: Revisited concepts %s should be ignored.\n" % parentconcept)
                        else:
                            sys.stderr.write("Wrong annotation format: Different concepts %s and %s have same node label(index)\n" % (amr.node_to_concepts[parentnodelabel],parentconcept))
                            parentnodelabel = parentnodelabel + "1"

                    if not isinstance(parentnodelabel,(Quantity,Polarity,StrLiteral)):                                       
                        # graph node rebuild
                        if parentconcept is not None:
                            amr.node_to_concepts[node_idx] = parentconcept
                            mapping_table[parentnodelabel] = node_idx
                            parentnodelabel = node_idx
                            node_idx += 1
                        else:
                            # not revisiting and concept is None
                            if parentnodelabel not in mapping_table:
                                amr.node_to_concepts[node_idx] = parentnodelabel
                                parentnodelabel = node_idx
                                node_idx += 1
                            else: #revisiting 
                                parentnodelabel = mapping_table[parentnodelabel]


                    for edgelabel,children in edges:
                        hypertarget = []
                        for node, concept in children:
                            if node is not None and not isinstance(node,(Quantity,Polarity,StrLiteral)):
                                if concept and not node in amr.node_to_concepts:
                                    print "CNODE",state,node,concept
                                    if node in mapping_table:
                                        node = mapping_table[node]
                                    else:
                                        amr.node_to_concepts[node_idx] = concept
                                        mapping_table[node] = node_idx
                                        node = node_idx
                                        node_idx += 1
                                elif concept is None and not node in amr.node_to_concepts:
                                    print "CNODE",state,node,concept
                                    if node in mapping_table:
                                        node = mapping_table[node]
                                    else:
                                        amr.node_to_concepts[node_idx] = node
                                        node = node_idx
                                        node_idx += 1

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
                    print "PNODE",state,parentnodelabel,parentconcept
                    
                    #check for annotation error
                    if parentnodelabel in amr.node_to_concepts.keys(): 
                        #concept has been defined by the children, 
                        #then they must have different concepts, otherwise the children's concepts should be None
                        #(coreference)
                        if amr.node_to_concepts[parentnodelabel] == parentconcept:
                            sys.stderr.write("Wrong annotation format: Revisited concepts %s should be ignored.\n" % parentconcept)
                        else:
                            sys.stderr.write("Wrong annotation format: Different concepts %s and %s have same node label(index)\n" % (amr.node_to_concepts[parentnodelabel],parentconcept))
                            parentnodelabel = parentnodelabel + "1"
                            
                    if not isinstance(parentnodelabel,(Quantity,Polarity,StrLiteral)):
                    # graph node rebuild
                        if parentconcept is not None:
                            amr.node_to_concepts[node_idx] = parentconcept
                            mapping_table[parentnodelabel] = node_idx
                            parentnodelabel = node_idx
                            node_idx += 1
                        else:
                            # not revisiting and concept is None
                            if parentnodelabel not in mapping_table:
                                amr.node_to_concepts[node_idx] = parentnodelabel
                                parentnodelabel = node_idx
                                node_idx += 1
                            else: #revisiting 
                                parentnodelabel = mapping_table[parentnodelabel]
                                

                    for edgelabel,children in edges:
                        hypertarget = []
                        for node, concept in children:
                            if node is not None and not isinstance(node,(Quantity,Polarity,StrLiteral)):
                                if concept and not node in amr.node_to_concepts:
                                    print "CNODE",state,node,concept
                                    if node in mapping_table:
                                        node = mapping_table[node]
                                    else:
                                        amr.node_to_concepts[node_idx] = concept
                                        mapping_table[node] = node_idx
                                        node = node_idx
                                        node_idx += 1
                                elif concept is None and not node in amr.node_to_concepts:
                                    print "CNODE",state,node,concept
                                    if node in mapping_table:
                                        node = mapping_table[node]
                                    else:
                                        amr.node_to_concepts[node_idx] = node
                                        node = node_idx
                                        node_idx += 1
                                
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
                else: raise ParserError, "Unexpected token %s"%(token.encode('utf8'))

            elif state == 7:
                if type == "IDENTIFIER":
                    stack.append((CNODE, token, None)) # another children
                    state = 6
                elif typpe == "LPAR":
                    state = 1
                else: raise ParserError, "Unexpected token %s"%(token)

        if state != 0 and stack: 
            raise ParserError, "mismatched parenthesis"
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
                   if warn:
                       warn.write("WARNING: (%s, %s, %s) produces a cycle with (%s, %s, %s)\n" % (parent, relation, child, c, rel, test))
                       #ATTENTION:maybe wrong, test may not have only one element, deal with it later
                       concept1 = self.node_to_concepts[parent]
                       concept2 = self.node_to_concepts[test[0]]
                       print concept1,concept2
                       if concept1 != concept2:
                           warn.write("ANNOTATION ERROR: concepts %s and %s have same node label %s!" % (concept1, concepts2, parent))
                       
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
                    
                    #print self.node_to_concepts
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
            Node.node_id = 0
            Node.mapping_table = {}
            sequences.append(all_nodes)
        
        return sequences
    def replace_node(self, h_idx, idx):
        """for coreference, replace all occurrence of node idx to h_idx"""
        visited_nodes = set()
        visited_edges = set()
        
        for i,r in enumerate(self.roots[:]):
            stack = [((r,),None,None)] #node,incoming edge and preceding node
            
            while stack:
                next, rel, previous = stack.pop()
                for n in next:
                    if n == idx:
                        if previous == None: # replace root
                            self.roots[i] = h_idx
                            break
                        self[previous].replace(rel,(h_idx,))
                    if n in visited_nodes:
                        continue
                    visited_nodes.add(n)
                    for rel, child in reversed(self[n].items()):
                        if not (n, rel, child) in visited_edges:
                            if child in visited_nodes:
                                stack.append((child,rel,n))
                            else:
                                visited_edges.add((n,rel,child))
                                stack.append((child,rel,n))
    def find_rel(self,h_idx,idx):
        """find the relation between head_idx and idx"""
        rels = []
        for rel,child in self[h_idx].items():
            print child,idx
            if child == (idx,):
                rels.append(rel)
        return rels

    def replace_head(self,old_head,new_head,KEEP_OLD=True):
        """change the focus of current sub graph"""
        for rel,child in self[old_head].items():
            if child != (new_head,):
                self[new_head].append(rel,child)
        del self[old_head]
        if KEEP_OLD:
            foo = self[old_head]
            self[new_head].append('NA',(old_head,))
    
    def replace_rel(self,h_idx,old_rel,new_rel):
        """replace the h_idx's old_rel to new_rel"""
        for v in self[h_idx].getall(old_rel):
            self[h_idx].append(new_rel,v)
        del self[h_idx][old_rel]
        
    def rebuild_index(self, node, sent_index_mapping=None):
        """assign non-literal node a new unique node label; replace the 
           original index with the new node id or sentence offset;
           if we have been provided the sentence index mapping, we use the 
           sentence offsets as new node label instead of the serialized node id.
        """
        if sent_index_mapping is None:
            if node.node_label in self.node_to_concepts and self.node_to_concepts[node.node_label] is not None:
                #update the node_to_concepts table 
                self.node_to_concepts[Node.node_id] = self.node_to_concepts[node.node_label]
                del self.node_to_concepts[node.node_label]
                Node.mapping_table[node.node_label] = Node.node_id
                node.node_label = Node.node_id 
                
            elif self.node_label not in node_to_concepts and self.node_label in Node.mapping_table:
                new_label = Node.mapping_table[self.node_label]
                self.node_label = new_label
            else:
                print Node.node_id,self.node_label
                node_to_concepts[Node.node_id] = self.node_label
                self.node_label = Node.node_id

            
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
                            amr_string += "\n%s:%s %s"%(node.depth*"\t",node.trace,node.node_label)
                            
                    else:
                        if node.firsthit and node.node_label in self.node_to_concepts:
                            amr_string += "\n%s:%s (%s / %s)"%(node.depth*"\t",node.trace,node.node_label,self.node_to_concepts[node.node_label])
                        else:
                            if isinstance(node.node_label,StrLiteral):
                                amr_string += '\n%s:%s "%s"'%(node.depth*"\t",node.trace,node.node_label)
                            else:
                                amr_string += "\n%s:%s %s"%(node.depth*"\t",node.trace,node.node_label)
                            
            if dep_rec != 0:
                amr_string += "%s"%((dep_rec)*')')

        return amr_string

if __name__ == "__main__":

    opt = OptionParser()
    opt.add_option("-v", action="store_true", dest="verbose")
    
    (options, args) = opt.parse_args()

    s = '''(a / and :op1(恶化 :ARG0(它) :ARG1(模式 :mod(开发)) :time (已经)) :op2(t / 堵塞 :ARG0(它) :ARG1(交通 :mod(局部)) :location(a / around :op1(出口))))'''
    s1 = '''(a  /  and :op1 (c  /  change-01 :ARG0 (i  /  it) :ARG1 (p  /  pattern :mod (d  /  develop-02)) :ARG2 (b  / bad :degree (m  /  more))) :op2 (c2  /  cause-01 :ARG0 i :ARG1 (c3  /  congest-01 :ARG1 (a2  /  around :op1 (e  /  exit :poss i)) :ARG2 (t  /  traffic) :ARG1-of (l2  /  localize-01))) :time (a3  /  already))'''
    s = s.decode('utf8')
    #import pdb 
    #pdb.set_trace()
    amr_ch = AMR.parse_string(s)
    #amr_en = AMR.parse_string(s1)
    
    #print str(amr_en)
    #print amr_en.dfs()
    #print amr_en.to_amr_string()
    print amr_ch
    #print amr_ch.dfs()
    print amr_ch.to_amr_string()
