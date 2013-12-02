"""
utilizations for amr graph representaion

@author: Chuan Wang
@since: 2013-11-20
"""

from collections import defaultdict



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

