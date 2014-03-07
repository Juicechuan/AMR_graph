'''
@date Jan 15, 2014
@author chuan wang
'''

from chn_head import head
from on.corpora import tree
import re,codecs
import on
from graph_reader.amr_graph import *

class Conversion():
    '''
    class for converting syntac structure parse tree into semantic structure amr 
    with extra information: propbank, name entity and coreference, etc.  
    '''
    def __init__(self):
        # each document has several coreference chain
        self.coref_chains = None

    def loadOntonotes(self):
        """
        load banks from ontonote
        See on/__init__.py for usages of ontonotes object
        """

        '''
        Create a config object and parse the command line options and arguments
        '''
        cfg = on.common.util.load_options(positional_args=True)
        #print "cfg:",cfg[1][0]
        '''
        get headrules
        '''
        #headrules = cfg[1][0]
        head_trees_path = cfg[1][0]
        '''
        Create an ontonotes object by passing in a config object
        '''

        a_ontonotes = on.ontonotes(cfg[0])
        return (a_ontonotes,head_trees_path)

    def convertTrees(self,a_ontonotes,head_trees):
        """
        given an ontonotes object and iterate over the 
        subcorpora it contains (usually only one subcorpus)
        a_subcorpus is a dictionary, containing a treebank for all fileids, a document and
        generally contains other banks.
        """
        def fix_coref(amr,coref_chains):
            "add within sentence coreference information to the amr."
            def determine_origin(links):
                """Here we use heuristic method to determine the referent in the coreference chain:
                the longest link string will be the referent.
                """
                return max(links, key=lambda link: len(link[1].string))

            for chain_id,links in coref_chains.items():
                if len(links) > 1:
                    h_index,ref_link = determine_origin(links)
                    for idx,link in links:
                        if idx != h_index:
                            amr.replace_node(h_index,idx)
        def fix_main_verb_be(amr,a_tree):
            """three conditions for main verb be"""
            def NPContainsWHXP(NPSubtree):
                """A noun clause"""
                for child in NPSubtree:
                    if child.is_trace() and re.match('WH.P',child.parent.tag):
                        return child.parent
                return False
            def getChildId(parent_tree,tr):
                for k,ch in enumerate(parent_tree.children):
                    if ch.id == tr.id:
                        break
                return k
            def getNPSbj(VCSubtree):
                """check whether current main verb be has NP as subject"""
                cur_tree = VCSubtree
                if cur_tree.parent == None:
                    return False
                while cur_tree.parent != None and cur_tree.parent.tag == 'VP':
                    cur_tree = cur_tree.parent
                i = getChildId(cur_tree.parent,cur_tree)
                assert i > 0
                result_subtree = cur_tree.parent.children[i-1]
                if result_subtree.tag.startswith('NP'):
                    return result_subtree
                else:
                    return None

            leaf_idx = None
            for j,lf in enumerate(a_tree):
                if lf.tag == 'VC':
                    leaf_idx = j
                    break
                

            if leaf_idx and amr[leaf_idx].items() != []:
                npsbj_tree = getNPSbj(a_tree[leaf_idx])
                if npsbj_tree:
                    if not NPContainsWHXP(npsbj_tree):
                        VCParent = a_tree[leaf_idx].parent
                        pos_tag_pattern = ''.join(c.tag for c in VCParent.children)
                        if re.match(r'VCNP-PRD',pos_tag_pattern):
                            amr.replace_rel(leaf_idx,u'ARG1',u'domain-of')
                        elif re.match(r'VC(PU)?IP-PRD',pos_tag_pattern):
                            amr.replace_rel(leaf_idx,u'ARG1',u'domain')
                        else:
                            print 'The predicate of main verb be is %s'%(pos_tag_pattern)
                        arg0_idx = amr[leaf_idx][u'ARG0'][0]
                        amr.replace_head(leaf_idx,arg0_idx,KEEP_OLD=False)
                        amr.replace_node(arg0_idx,leaf_idx)
                    else:
                        identity_subtree = NPContainsWHXP(npsbj_tree)
                        identity_idx = identity_subtree.get_token_index()
                        arg1_idx = amr[leaf_idx][u'ARG1'][0]
                        arg0_idx = amr[leaf_idx][u'ARG0'][0]
                        for rleave in identity_subtree.reference_leaves:
                            rl_idx = rleave.get_token_index()
                            if rl_idx in amr: # not handled by relative clause, treat it as noun clause
                                amr.replace_node(arg1_idx,rl_idx)
                                amr.replace_node(arg0_idx,leaf_idx)
                            else:
                                pass

        for a_subcorpus in a_ontonotes:
            a_tree_bank = a_subcorpus['parse']
            #import pdb
            #pdb.set_trace()
            '''
            The treebank class represents a collection of :class:`tree_document` classes
            '''
            for a_tree_document in a_tree_bank:
                '''
                The tree_document class contains a collection of trees
                '''
                print "current file id is ",a_tree_document.document_id, " including ", len(a_tree_document.tree_ids)," trees"
                doc_id = a_tree_document.document_id.split('@',1)[0].split('/')[0] + '.' + a_tree_document.document_id.split('@',1)[0].split('/')[-1]
                wf = codecs.open('camr_'+doc_id+'.txt','w','utf8')
                empty_amr = [6,7,45,46,65,71,95,96]
                a_tree_docgen = [(atid,at) for atid,at in enumerate(a_tree_document[:101]) if atid not in empty_amr]
                for tid,a_tree in a_tree_docgen:
                    self.coref_chains = defaultdict(list)
                    print "current file id is ", a_tree.document_id," current tree id is ", a_tree.id
                    print a_tree.pretty_print()
                    print a_tree.get_word_string()
                    wf.write('# ::id %s.%s\n'%(doc_id,tid+1))
                    wf.write('# ::zh %s\n'%(a_tree.get_word_string()))
                    wf.write('\n')
                    
                    amr = AMR()
                    
                    rel, root = self.convert(head_trees, a_tree, amr)
                    assert rel == None
                    amr.roots = [root]
                    print "converted amr"
                    print amr.to_amr_string()
                    print "fix coreference"
                    fix_coref(amr,self.coref_chains)
                    fix_main_verb_be(amr,a_tree)
                    print amr.to_amr_string()
                    wf.write(amr.to_amr_string())
                    wf.write('\n')
                    wf.write('\n')
                    #print converted_tree.pretty_print()
                    #rec_num = 0
                    #var_dict = {}
                    #converted_str = at.toString(converted_tree,rec_num, var_dict)
                    #print converted_str
                    #raw_input("Press ENTER to continue")
                wf.close()
    def get_edge_labels(self, a_tree):
        """
        return all propbank args, functional tag and name entity information for the current node
        """
        arg_func_tags = {}
        if len(a_tree.argument_node_list) > 0:
            '''
            current tree is an argument in propbank
            '''
            print a_tree.tag+" GetRole:"+''.join(x.argument.type for x in a_tree.argument_node_list)
            arg_func_tags["PRED-ARG"] = [(arg.proposition.predicate.token_index,arg.argument.type) for arg in a_tree.argument_node_list]
                                         
            
        if a_tree.compound_function_tag != []:
            '''
            get functional tag
            '''
            print a_tree.tag+" functional tag:"+str(a_tree.compound_function_tag.function_tag_types)
            arg_func_tags["FUNCT"] = "-".join(a_tree.compound_function_tag.function_tag_types)
            
        if a_tree.name_type != None:
            print "name entity",a_tree.name_type, a_tree.get_word_string()
            arg_func_tags["ENTITY"] = a_tree.name_type

        return arg_func_tags

    def getArgType(self,amr,a_tree,child_token_idx,head_token_idx):
        """get the arg type (argx-of) of the relative clause"""
        def isArgTrace(a_tree,offset=None,a_argument_idx=None,start=None):
            if offset == None:
                a_leaf = a_tree[a_argument_idx-start]
            else:
                a_leaf = a_tree[offset]
            if a_leaf.is_trace():
                if a_leaf.identity_subtree is None: # dropped *pro* has no identity subtree
                    return False
                elif a_leaf.identity_subtree.tag.startswith('WH'): # operation *OP*
                    return True
            return False

        def getIdentTrace(a_tree,offset=None,a_argument_idx=None,start=None): # get *T*-X identity trace WHXP -NONE- *OP*
            if offset == None:
                a_leaf = a_tree[a_argument_idx-start]
            else:
                a_leaf = a_tree[offset]
            if not a_leaf.is_trace(): # semantic label mistake
                return None
            return a_leaf.identity_subtree
        
        def fetch_subtree_span(a_tree,subtree_idx,subtree_height,start):
            """get the index span of the subtree start token index 'subtree_idx' """
            cur_tree = a_tree[int(subtree_idx)-start]
            i = int(subtree_height)
            while i > 0:
                cur_tree = cur_tree.parent
                i -= 1
            return (cur_tree.start,cur_tree.end)

        def find_arg_type(a_tree,a_analogue,head_token_idx,start):
            traces = []
            for a_argument in a_analogue:
                if len(a_argument.enc_self.split(':')) > 2:
                    sub_idx = a_argument.enc_self.split(':')[0]
                    sub_height = a_argument.enc_self.split(':')[1].split(',')[0]
                elif len(a_argument.enc_self.split(':')) == 2:
                    sub_idx,sub_height = a_argument.enc_self.split(':')

                a_argument_span = fetch_subtree_span(a_tree,sub_idx,sub_height,start)
                if  a_argument_span[0] <= head_token_idx <= a_argument_span[1]:
                    argType = a_analogue.type
                else: # here assume trace argument and its identity trace is a pair,e.g. *OP* <-> *T*-2
                    ident_trace = getIdentTrace(a_tree,a_argument_idx=int(sub_idx),start=start)
                    if ident_trace:
                        trace_idx = ident_trace.get_token_index()
                        if not ident_trace.is_leaf():
                            trace_leaf = ident_trace[0]
                            next_trace = getIdentTrace(a_tree,a_argument_idx=trace_idx,start=start)
                            if next_trace:
                                traces.append((trace_idx,next_trace.get_token_index()))
                        traces.append((int(sub_idx),trace_idx))
                    else:
                        return None,traces
            return argType,traces

        start = a_tree.get_token_index()
        pred_idx = child_token_idx - start
        

        #print child_token_idx
        #print a_tree.pretty_print()


        if len(a_tree[pred_idx].predicate_node_list) > 0:         # Condition 1
            a_argument_analogues = a_tree[pred_idx].predicate_node_list[0].proposition.argument_analogues
        

            argType = None
            for a_analogue in a_argument_analogues:
                if len(a_analogue) > 1: # current predicate's argument has a coreferential trace  
                    argType,traces = find_arg_type(a_tree,a_analogue,head_token_idx,start)
                    if argType != None: 
                        return (None,argType,traces)
             # PAIN OF WORKING WITH NONCONSISTENT ANNOTATION(PWNA): the trace is not labeled 'coreference' with the actual argument but we can find the trace and make it corefer with the actual argument
            for a_analogue in a_argument_analogues:
                for a_argument in a_analogue:
                    a_argument_idx = int(a_argument.enc_self.split(':')[0])
                    if isArgTrace(a_tree,a_argument_idx=a_argument_idx,start=start):
                        return (None,a_analogue.type,[(a_argument_idx,getIdentTrace(a_tree,a_argument_idx=a_argument_idx,start=start))])
        else:
            # the predicate is even not labeled in the propbank!!!
            # option1: there is something wrong with the head rule, we need to use another verb head
            # option2: head rule is correct, but the verb inside relative clause is not labeled as predicate we just take the empty category trace's type as the argument type
            for i,leaf in enumerate(a_tree):
                if i != pred_idx and len(a_tree[i].predicate_node_list) > 0: # Condition 2: this is the predicate/head
                    a_argument_analogues = a_tree[i].predicate_node_list[0].proposition.argument_analogues
                    argType = None
                    for a_analogue in a_argument_analogues:
                        if len(a_analogue) > 1: # current predicate's argument has a coreferential trace  
                            argType,traces = find_arg_type(a_tree,a_analogue,head_token_idx,start)
                            if argType != None: 
                                return (i+start,argType,traces)

                if i != pred_idx and isArgTrace(a_tree,offset=i):             # Condition 3
                    rel_type = amr.find_rel(child_token_idx,i+start)                 
                    print "trace relation %s %s:%s"%(a_tree[pred_idx].pretty_print(),a_tree[i].pretty_print(),rel_type)
                    assert len(rel_type)==1
                    return (None,rel_type[0],[(i+start,getIdentTrace(a_tree,offset=i))])

        raise Exception('Cannot find arg type for predicate:%s argument:%s'%(child_token_idx,head_token_idx))

    def convertRC(self,amr,a_tree,spec_child_token_idx,head_token_idx):
        new_spec_child_idx,arg_type,traces = self.getArgType(amr,a_tree,spec_child_token_idx,head_token_idx)
        
        if new_spec_child_idx != None:
            amr.replace_head(spec_child_token_idx,new_spec_child_idx)
            spec_child_token_idx = new_spec_child_idx
            
        for tr_idx,ident_idx in traces:                 
            print arg_type,tr_idx
            if (arg_type,(tr_idx,)) in amr[spec_child_token_idx].items():
                amr[spec_child_token_idx].remove(arg_type,(tr_idx,))
                if tr_idx in amr:
                    del amr[tr_idx]
            if ('NA',(ident_idx,)) in amr[spec_child_token_idx].items():
                amr[spec_child_token_idx].remove('NA',(ident_idx,))
                if ident_idx in amr:
                    del amr[ident_idx]
            argType = arg_type
            
        amr._add_triple(head_token_idx,argType+'-of',spec_child_token_idx)
    def convertPN(self,a_tree,amr,rel,head_token_idx):
        """convert proper noun"""
        head_token_idx = a_tree.start
        name_idx = 'e'+str(head_token_idx)
        foo = amr[name_idx]
        amr.node_to_concepts[name_idx] = 'name'
        k = 0
        for child_id, child in enumerate(a_tree):
            if child.tag not in ['PU','CC']:
                k += 1
                concept = child.word
                opNum = 'op'+str(k)
                amr._add_triple(name_idx, opNum, StrLiteral(concept))
        amr._add_triple(head_token_idx, 'name', name_idx)
        amr.node_to_concepts[head_token_idx] = 'TBD-entity-type'
        if isinstance(rel,unicode):
            rel = rel.split('-')
            rel.remove(u'PN')
            if rel:
                rel = '-'.join(t for t in rel)
            else:
                rel = None
        return (rel,head_token_idx)
    
    def convert(self, head_trees, a_tree, amr):
        """
        recursively convert a tree/subtree into amr  
        """

        #if a_tree.tag == 'DNP':
        #    import pdb
        #    pdb.set_trace()
        def getDNPType(a_tr,h_id,sc_id):
            """DNP types """
            a_DNP_tree = a_tr.children[sc_id]
            tag_pattern = '+'.join(x.tag.split('-')[0] for x in a_DNP_tree.children)
            return tag_pattern
            
        def isPredicate(a_tr,h_idx):
            """check whether the current verb head is a predicate in propbank"""
            relative_idx = h_idx - a_tr.get_token_index()
            head_node = a_tr[relative_idx]
            if head_node.tag == 'VV':
                import pdb
                pdb.set_trace()
                return head_node.proposition != None 
            else:
                return True

        def fix_predicate(amr,a_tree,h_idx):
            """fix the current amr by eliminating the non-predicate (in propbank) head
               here maybe a little confused since the predicates in propbank are not always
               the head in the treebank.
            """
            pass
            
        def convertCompVerb(h_child,amr,h_idx):
            """combine VSB's two VV as one"""
            del amr[h_idx]
            foo = amr[h_idx]
            amr.node_to_concepts[h_idx] = ''.join(x.word for x in h_child.children)
            
        def isVPCoordination(a_tr):
            """VP(VP(...)PU(,)VP(...))"""
            if a_tr.tag == 'VP' and re.match('VPPUVP',''.join(x.tag for x in a_tr.children)):
                return True
            else:
                return False
        def recover_subject(amr,head_token_idx):
            arg0 = None
            for op in amr[head_token_idx].values():
                subject = amr[op[0]].itemsfor('ARG0')
                if subject != []:
                    arg0 = subject[0][1]
            for vp in amr[head_token_idx].values():
                subject = amr[vp[0]].itemsfor('ARG0')
                if subject == []:
                    amr._add_triple(vp[0],'ARG0',arg0)

        
        he = head()
        modifier_structs,head_child_id = he.getHeadNodeTree(head_trees, a_tree)
        
        #propbank args and functional tags for current tree node/leaf
        aftags = {}
        pred_args = self.get_edge_labels(a_tree)
        
        rel = None
        ftag = None
        if "PRED-ARG" in pred_args:
            rel = pred_args["PRED-ARG"]
        if "FUNCT" in pred_args:
            ftag = pred_args["FUNCT"]

        if not rel and ftag:
            rel = ftag

        if a_tree.is_leaf():
            #if a_tree.word in [u'\u3002',u'\u300a',u'\uff01']: #punctuation
            #    return (None,)
            token_idx = a_tree.get_token_index()
            if a_tree.tag in ['PU','CS','SP','DEC','AS']:
                return (-1, token_idx)
            foo = amr[token_idx]  #add only the node with no children
            amr.node_to_concepts[token_idx] = a_tree.word #update the node_id->concept mapping
            return (rel,token_idx)
        else:
            head_rel, head_token_idx = self.convert(head_trees, a_tree.children[head_child_id], amr)        
            opNum = 1
            head_child = a_tree.children[head_child_id]
            

            # deal with compound verb
            if head_child.tag in ['VSB','VRD','VCD','VNV']:
                convertCompVerb(head_child,amr,head_token_idx)

            if head_rel == -1:
                if head_child.tag == 'PU':  # cannot drop conjunction head: the comma
                    foo = amr[head_token_idx]
                else:
                    rel = head_rel
            
            # coreference
            if a_tree.coreference_link and a_tree.coreference_chain.type == 'IDENT':
                self.coref_chains[a_tree.coreference_chain.id].append((head_token_idx,a_tree.coreference_link))
            
            if ftag and 'PN' in ftag.split('-'):
                return self.convertPN(a_tree,amr,rel,head_token_idx)
                
            if modifier_structs == {}:
                for child_id, child in enumerate(a_tree.children):            
                    if child_id != head_child_id:
                        child_rel,child_token_idx = self.convert(head_trees, child, amr)   
                        if child_rel == None:
                            amr._add_triple(head_token_idx, "NA", child_token_idx)
                        elif isinstance(child_rel,list):
                            for pred,arg in child_rel:
                                amr._add_triple(pred, arg, child_token_idx)
                        elif isinstance(child_rel,unicode):
                            if child_rel == u'OBJ':
                                child_rel = 'ARG1'
                            elif child_rel == u'SBJ' or child_rel.split('-')[-1] == u'SBJ':
                                child_rel = 'ARG0'
                            amr._add_triple(head_token_idx, child_rel, child_token_idx)
                        elif child_rel == -1:
                            continue
                        else:
                            print a_tree.pretty_print()
                            raise TypeError('Wrong relation types: %s,%s'%(child_rel,child_rel.__class__.__name__))
                if head_rel == 'VPCOORD':
                    recover_subject(amr,head_token_idx)

            elif 'CONJUNCTION' in modifier_structs:
                assert len(modifier_structs) == 1
                for child_id, child in enumerate(a_tree.children):
                    if child_id != head_child_id:
                        child_rel,child_token_idx = self.convert(head_trees, child, amr)   
                        # if child_rel == PN convertPN
                        print child_rel,child_token_idx

                        if child_rel == -1: # punctuation
                            continue
                        elif isinstance(child_rel,list):
                            for pred,arg in child_rel:
                                amr._add_triple(pred, arg, child_token_idx)
                        elif isinstance(child_rel,unicode):
                            pass
                        elif child_rel == None or child_rel == -1 or child_rel == 'PN' or child_rel == 'Q':
                            pass
                        else:
                            raise TypeError('Wrong relation types: %s,%s'%(child_rel,child_rel.__class__.__name__))
                        amr._add_triple(head_token_idx, "op"+str(opNum), child_token_idx)
                        amr.node_to_concepts[head_token_idx] = 'and'
                        opNum+=1
                if isVPCoordination(a_tree):
                    assert rel == None
                    rel = 'VPCOORD'
 
            else:  # current tree contains various kind of adjunction subtree
                spec_id_list = []
                # first deal with the adjunct subtrees
                for modifier in modifier_structs: 
                    spec_child_id = modifier_structs[modifier]
                    spec_id_list.append(spec_child_id)

                    if modifier == 'RELATIVE-CLAUSE':
                        spec_child = a_tree.children[spec_child_id]
                        spec_child_rel,spec_child_token_idx = self.convert(head_trees, spec_child, amr)

                        if amr.node_to_concepts[spec_child_token_idx] == 'and': # conjunction
                            for relation,op in amr[spec_child_token_idx].items():
                                if relation.startswith('op'):
                                    self.convertRC(amr,a_tree,op[0],head_token_idx)
                        else:
                            self.convertRC(amr,a_tree,spec_child_token_idx,head_token_idx)

                        
                    elif modifier == 'CND':
                        spec_child = a_tree.children[spec_child_id]
                        spec_child_rel,spec_child_token_idx = self.convert(head_trees, spec_child, amr)
                        amr._add_triple(head_token_idx, 'condition', spec_child_token_idx)
                    elif modifier == 'BA':
                        spec_child = a_tree.children[spec_child_id]
                        # here we simply don't add the BA 
                    elif modifier == 'DNP-NMOD':
                        assert spec_child_id != -1
                        DNP_TYPE = getDNPType(a_tree,head_child_id,spec_child_id)
                        # different categories of complements in DNP
                        if DNP_TYPE == 'PP+DEG':
                            spec_child = a_tree.children[spec_child_id]
                            spec_child_rel,spec_child_token_idx = self.convert(head_trees, spec_child, amr)
                            assert spec_child_rel == None
                            assert spec_child.children[-1].tag == 'DEG'
                            rel_child_pairs = amr[spec_child_token_idx].items()
                            assert len(rel_child_pairs) == 1
                            pp_rel = rel_child_pairs[0][0]
                            pp_idx = rel_child_pairs[0][1]
                            del amr[spec_child_token_idx]
                            amr._add_triple(head_token_idx,pp_rel,pp_idx)
                            
                            for poss_id in [spec_child_id - 1,spec_child_id + 1]:
                                if poss_id >= 0 and poss_id < len(a_tree.children) and poss_id != head_child_id:
                                    poss_child = a_tree.children[poss_id]
                                    poss_child_rel,poss_child_token_idx = self.convert(head_trees,poss_child, amr)
                                    assert poss_child_rel == None
                                    amr._add_triple(head_token_idx,'poss',poss_child_token_idx)
                                    spec_id_list.append(poss_id)

                        elif DNP_TYPE in ['NP+DEG','DP+DEG','ADJP+DEG']:

                            spec_child = a_tree.children[spec_child_id]
                            spec_child_rel,spec_child_token_idx = self.convert(head_trees,spec_child, amr)
                            assert spec_child_rel == None
                            assert spec_child.children[-1].tag == 'DEG'
                            rel_child_pairs = amr[spec_child_token_idx].items()
                            assert len(rel_child_pairs) == 1
                            xp_rel = rel_child_pairs[0][0]
                            # if xp_rel == 'PN': convertPN
                            assert xp_rel == None or xp_rel == -1 or xp_rel == 'PN' or xp_rel == 'NA'
                            xp_idx = rel_child_pairs[0][1]
                            del amr[spec_child_token_idx]
                            amr._add_triple(head_token_idx,'mod',xp_idx)
                                        
                    elif modifier.startswith('PP'): # preposition
                        PP_TYPE = modifier.split('-')[-1]
                        
                        if spec_child_id != head_child_id:
                            spec_child = a_tree.children[spec_child_id]
                            spec_child_rel,spec_child_token_idx = self.convert(head_trees,spec_child, amr)
                            # print spec_child_rel
                            # NEED CHECK here:assert spec_child_rel ==  None
                            # get complement of preposition
                            #print spec_child.pretty_print()
                            #print spec_child_token_idx
                            #print amr[spec_child_token_idx].values()

                            relative_token_idx = spec_child_token_idx - spec_child.get_token_index()
                            if spec_child[relative_token_idx].tag == 'P':
                                # only one node(complement) follow preposition
                                # assert len(amr[spec_child_token_idx].values()) == 1 or len(amr[spec_child_token_idx].values()) == 0
                                if len(amr[spec_child_token_idx].values()) == 0:
                                    continue

                                complement_idx = amr[spec_child_token_idx].values()[-1]
                                del amr[spec_child_token_idx] # here we eliminate the prepoision within PP replace it with :prep-x
                                amr._add_triple(head_token_idx,'prep-'+PP_TYPE,complement_idx)
                            else:
                                # add the child as normal 
                                spec_id_list.pop()

                        else:
                            relative_token_idx = head_token_idx - head_child.get_token_index()
                            if head_child[relative_token_idx].tag == 'P':
                                # only one node(complement) follow preposition
                                assert len(amr[head_token_idx].values()) == 1 or len(amr[head_token_idx].values()) == 0
                                if len(amr[head_token_idx].values()) == 0:
                                    continue
                                complement_idx = amr[head_token_idx].values()[0]
                                del amr[head_token_idx] # here we eliminate the prepoision within PP replace it with :prep-x
                                head_token_idx = complement_idx[0]
                                PP_TYPE = head_child.tag.split('-')[-1]
                                rel = 'prep-'+PP_TYPE
                            else:
                                spec_id_list.pop()
                            

                            

                        
                    else:
                        raise TypeError('Wrong modifier_type: %s'%(modifier))
                
                # add other relation subtrees
                for child_id, child in enumerate(a_tree.children):
                    if child_id != head_child_id and child_id not in spec_id_list:
                        child_rel,child_token_idx = self.convert(head_trees, child, amr)   
                        
                        if child_rel == None:
                            amr._add_triple(head_token_idx, "NA", child_token_idx)
                        elif isinstance(child_rel,list):
                            for pred,arg in child_rel:
                                amr._add_triple(pred, arg, child_token_idx)
                        elif isinstance(child_rel,unicode):
                            if child_rel == u'OBJ':
                                child_rel = 'ARG1'
                            elif child_rel == u'SBJ':
                                child_rel = 'ARG0'
                            amr._add_triple(head_token_idx, child_rel, child_token_idx)
                        elif child_rel == -1:
                            continue
                        else:
                            raise TypeError('Wrong relation types: %s,%s'%(child_rel,child_rel.__class__.__name__))
            
            # fix logistic subject
            if 'prep-LGS' in amr[head_token_idx] and amr[head_token_idx].itemsfor('ARG0') != []:
                amr[head_token_idx].replace('ARG0',amr[head_token_idx]['prep-LGS'])
                del amr[head_token_idx]['prep-LGS']
                        
            return rel, head_token_idx




def main():
    cconv = Conversion()
    he = head()
    a_ontonotes,head_trees_path = cconv.loadOntonotes()
    #head_rules = he.loadHeadrules("/nfs/guest/yaqiny/Dropbox/Code/OntonotesUtil/ontonotes-db-tool-v0.999b/data/headrules.txt")
    #head_rules = he.loadHeadrules("/home/j/llc/cwang24/R_D/AMR/ontonotes-db-tool-v0.999b/data/headrules.txt")
    head_trees = he.loadHeadTrees(head_trees_path)
    cconv.convertTrees(a_ontonotes,head_trees)
    
if __name__=="__main__":
    main()
