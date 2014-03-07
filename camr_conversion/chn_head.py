'''
Created on Jun 18, 2012
Updated on Oct 10, 2013

@author: yaqin276
'''
import re
import codecs
from nltk.tree import Tree

class TreeHeadException(Exception):
    pass

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
            [tag, cate] = line.strip().split("\t")
            if tag not in rules:
                rules[tag] = []
                temp = map(lambda x:x.split(" "),cate.split(";"))
                rules[tag].append(temp)
        return rules

    def loadHeadTrees(self,filename):
        """load trees with head annotated with ps2ds"""
        trees = []
        inf = codecs.open(filename,'r','utf-8')
        for s in inf.readlines():
            head_tree = Tree.parse(s)
            head_tree = Tree('TOP',[head_tree]) # coordinate with original tree structure
            trees.append(head_tree)
        return trees
            
    def getHeadNodeTree(self,head_trees,a_tree):
        """get head node from head annotated trees
           And return current subtree's phrase structure
           return head_type,spec_sibling_id,head_id tuple
        """

        def getPP(tags): 
            return [(i,tag) for i,tag in enumerate(tags) if tag.startswith('PP')]

        parts = a_tree.id.split('@',1)
        first_part = parts[0]
        rest_part = parts[1]

        #head_type = None
        spec_sibling_id = -1
        modifier_structs  = {} # modifier:id 
        if ':' not in first_part: # is root
            current_tree = head_trees[int(first_part)]
            for child_id, child in enumerate(current_tree):
                head_tag = child.node.split('-')[-1]
                if head_tag == 'HEAD':
                    return (modifier_structs,child_id)
                elif head_tag == 'CONJUNCTION1': # conjunction right under the root
                    print "WARNING:conjunction right under the root!!!"
                    modifier_structs['CONJUNCTION'] = spec_sibling_id
                    return (modifier_structs,child_id)
            if len(current_tree) == 1:
                return (modifier_structs,0)
            else:
                raise TreeHeadException('Fail to choose a head %s'%(','.join(x.node for x in current_tree)))
        else:
            token_index = int(first_part.split(':')[0])
            height = int(first_part.split(':')[1])
            sentence_id = int(rest_part.split('@',1)[0])
            
            current_tree = head_trees[sentence_id]
            treepos = current_tree.leaf_treeposition(token_index)
            subtreepos = list(treepos)[:-height-1]
            
            def fix_NXCCNX(a_tree,subtreepos):
                if re.match('N[^P]CC(N[^P])+|(NNPU)+',''.join(x.tag for x in a_tree.children)):
                    subtreepos.pop()
                else:
                    if len(a_tree.children) > 0:
                        fix_NXCCNX(a_tree.children[0],subtreepos)

            # bugs for head tree: added node to NX+CC+NX
            #if re.match('N.CCN.',''.join(x.tag for x in a_tree.children)):
            #    subtreepos = subtreepos[:-1]

            fix_NXCCNX(a_tree,subtreepos)

            for i in subtreepos:
                current_tree = current_tree[i]
            
            if height > 0:

                add_tags = [x.node.split('-')[-1] for x in current_tree]
                tags = [x.node for x in current_tree]
                pos_tags = [x.node.split('-')[0] for x in current_tree]
            
                if 'HEAD' in add_tags:
                    head_child_id = add_tags.index('HEAD')

                    if a_tree.children[head_child_id].tag.split('-')[-1] == 'CND':  # condition should not be head
                        modifier_structs['CND'] = head_child_id
                        head_child_id = pos_tags.index('VP')
                    if a_tree.children[head_child_id].tag.split('-')[0] == 'BA': # BA construction we treat the verb inside the IP is head
                        modifier_structs['BA'] = head_child_id
                        head_child_id = pos_tags.index('IP')
                    if 'CP-CND' in tags:
                        modifier_structs['CND'] = tags.index('CP-CND')
                    if 'CP-RELATIVE' in tags: # current head is modified by a relative clause
                        if a_tree.children[tags.index('CP-RELATIVE')].tag.split('-')[-1] != 'APP': # here the relative rule made some mistake: APP
                            modifier_structs['RELATIVE-CLAUSE'] = tags.index('CP-RELATIVE')
                    if 'DNP-NMOD' in tags:  # current head (NP) is modified by a DNP structure
                        modifier_structs['DNP-NMOD'] =  tags.index('DNP-NMOD')
                    if getPP(tags) != []:
                        # PP may be head
                        #ASSUME: PP tags are all different within children's tags
                        for i,pp in getPP(tags):                            
                            modifier_structs[pp] = i
                    return (modifier_structs,head_child_id)
                elif 'CONJUNCTION1' in add_tags:
                    head_child_id = add_tags.index('CONJUNCTION1')
                    modifier_structs['CONJUNCTION'] = spec_sibling_id
                    return (modifier_structs,head_child_id)
                elif 'COMP' in add_tags:
                    head_child_id = add_tags.index('COMP')
                    return (modifier_structs,head_child_id)
                elif re.match('(CONJUNCT\d)+',''.join(x for x in add_tags)):
                    return (modifier_structs,0)
                elif len(current_tree) == 1:
                    return (modifier_structs,0)
                else:
                    raise TreeHeadException('Fail to choose a head %s'%(','.join(x.node for x in current_tree)))

            else:
                return (modifier_structs,0)
            '''
            for child_id, child in enumerate(current_tree):
                if isinstance(child,Tree):
                    head_tag = child.node.split('-')[-1]
                    if head_tag == 'HEAD':
                        # current tree's children's tag list
                        tag_list = [x.node for x in current_tree]
                        
                        if 'CP-RELATIVE' in tag_list: # current head is modified by a relative clause
                            spec_sibling_id = tag_list.index('CP-RELATIVE')
                            return ('RELATIVE-CLAUSE',spec_sibling_id,child_id)
                        elif 'DNP-NMOD' in tag_list:  # current head (NP) is modified by a DNP structure
                            spec_sibling_id = tag_list.index('DNP-NMOD')
                            return ('DNP-NMOD',spec_sibling_id,child_id)
                        return ('RULE',spec_sibling_id,child_id)
                    elif head_tag == 'CONJUNCTION1': 
                        return ('CONJUNCTION',spec_sibling_id,child_id)
                    elif head_tag == "COMP": # relative clause
                        return ('RULE',spec_sibling_id,child_id)
                else:
                    return ('RULE',spec_sibling_id,child_id)
             
        if len(current_tree) == 1:
            return ('RULE',spec_sibling_id,0)
        else:
            raise TreeHeadException('Fail to choose a head %s'%(','.join(x.node for x in current_tree)))
        '''
            


    def getHeadNode(self,rules,a_tree):
    	"""an updated version in case that under coordination (VP) in Chinese the head should be the comma or TBD"""
    	
        type="rule"  #the principle of identifying head
        if a_tree == None:
            return None
        if a_tree.tag.split("-")[0] not in rules:
            #print "tag not in the rules ",a_tree.tag
            return (type,0)
        #direction = rules[a_tree.tag.split("-")[0]][0]
        direct_cate = rules[a_tree.tag.split("-")[0]][0]
        head_id = 0
        
        children_list = a_tree.children
        child_tags = [x.tag for x in children_list]
        #coordination situation 1
        if re.match('(VPPU)+VP',''.join(child_tags)):
            pu_index = child_tags.index('PU')
            type = 'coordination1'
            if children_list[pu_index].word == u'\uff0c':
                return (type,pu_index)
        		
        #if direction in ["r"]:
        #    children_list.reverse()
        for dc in direct_cate:
            direction = dc[0]
            categories = dc[1:]
            if len(categories) == 0:
                categories = ['']
            if direction in ["r"]:
                children_list.reverse()
            for child_id, child in enumerate(children_list):
                child_tag = child.tag
                for cc in categories:
                    if re.match(cc,child_tag):
                        if direction in ["r"]:
                            children_list.reverse()
                            return (type,len(children_list) - child_id - 1)
                        else:
                            return (type,child_id)
    '''
    def getHeadNode(self,rules,a_tree):
        if a_tree == None:
            return None
        if a_tree.tag.split("-")[0] not in rules:
            #print "tag not in the rules ",a_tree.tag
            return 0
        #direction = rules[a_tree.tag.split("-")[0]][0]
        direct_cate = rules[a_tree.tag.split("-")[0]][0]
        head_id = 0
        
        children_list = a_tree.children
        #if direction in ["r"]:
        #    children_list.reverse()
        for dc in direct_cate:
            direction = dc[0]
            categories = dc[1:]
            if len(categories) == 0:
                categories = ['']
            if direction in ["r"]:
                children_list.reverse()
            for child_id, child in enumerate(children_list):
                child_tag = child.tag
                for cc in categories:
                    if re.match(cc,child_tag):
                        if direction in ["r"]:
                            children_list.reverse()
                            return len(children_list) - child_id - 1
                        else:
                            return child_id
    '''
                        
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
    
                
                
                
                
                
                
                
                
                
            
        
        
