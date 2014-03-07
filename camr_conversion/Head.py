'''
Created on Jun 18, 2012

@author: yaqin276
'''
import re

class head(object):
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
    def loadHeadrules(self,file):
        input = open(file,"r")
        rules = {}
        for line in input:
            if len(line.strip()) == 0:
                continue
            [tag, direction, cate] = line.strip().split()
            if tag not in rules:
                rules[tag] = []
                rules[tag].append(direction)
                temp = map(lambda x:x.split("|"),cate.split(";"))
                rules[tag].append(temp)
        return rules
    
    def getHeadNode(self,rules,a_tree):
        if a_tree == None:
            return None
        if a_tree.tag.split("-")[0] not in rules:
            #print "tag not in the rules ",a_tree.tag
            return 0
	#import pdb
	#pdb.set_trace()
        direction = rules[a_tree.tag.split("-")[0]][0]
        categories = rules[a_tree.tag.split("-")[0]][1]
        head_id = 0
        
        children_list = a_tree.children
        if direction in ["r"]:
            children_list.reverse()
        for c in categories:
            for child_id, child in enumerate(children_list):
                child_tag = child.tag
                for cc in c:
                    if re.match(cc.split(".")[0],child_tag):
                        if direction in ["r"]:
                            children_list.reverse()
                            return len(children_list) - child_id - 1
                        else:
                            return child_id
                        
    def isHeadLeaf(self,rules,antecedent,leaf):
        parent_node = leaf.parent
        cur_node = leaf
        while parent_node != antecedent:
            cur_index = cur_node.child_index
            head_index = self.getHeadNode(rules, parent_node)
            if cur_index != head_index or cur_index == None or head_index == None:
                return False
            cur_node = parent_node
            parent_node = parent_node.parent
            
        if parent_node == antecedent:
            return True
        return False
            
    def isCopula(self, a_tree, head_child_id):
        '''
        if the head is a copula verb
        '''
        if a_tree.children[head_child_id].is_leaf():
            head_word = a_tree.children[head_child_id].word.lower()
            if head_word not in ["is","was","are","were"]:
                return False
            if len(a_tree.children) > head_child_id + 1:
                right_sibling_tag = a_tree.children[head_child_id+1].tag
                if re.match("V",right_sibling_tag):
                    return False
                return True
        return False
    
                
                
                
                
                
                
                
                
                
            
        
        
