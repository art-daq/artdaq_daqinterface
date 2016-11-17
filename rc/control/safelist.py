import copy
import threading


class SafeList(object):
    """
    Provides a thread-safe list with basic locking, append, remove,
    and find semantics.
    """
    def __init__(self, coll=None):
        self.__lock = threading.Lock()
        self.__coll = [] if coll is None else coll

    def __len__(self):
        with self.__lock:
            return len(self.__coll)

    def append(self, x):
        with self.__lock:
            self.__coll.append(x)

    def find(self, f):
        with self.__lock:
            return [x for x in self.__coll if f(x)]

    def remove(self, f):
        with self.__lock:
            self.__coll = [x for x in self.__coll if not f(x)]
            return self

    def map(self, f):
        """
        Apply `f` successively to all elements and return resulting list.
        """
        with self.__lock:
            return [f(x) for x in self.__coll]

    def list(self):
        """
        Safely return a copy of the list of items.  Does not do a deep copy.
        """
        with self.__lock:
            return copy.copy(self.__coll)

    def add_or_update(self, f, new_el):
        """
        Safely add or update an item with search criteria provided by
        function `f`. If no items are found, append `new_el`. If more
        than one items are found, the first will be updated by
        substituting `new_el`.
        """
        with self.__lock:
            existing = [i for (i, x) in enumerate(self.__coll)
                        if f(x)]
            if not existing:
                self.__coll.append(new_el)
            else:
                self.__coll[existing[0]] = new_el
