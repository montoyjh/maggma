from abc import ABCMeta, abstractmethod
import logging

from monty.json import MSONable, MontyDecoder


class Builder(MSONable, metaclass=ABCMeta):

    def __init__(self, sources, targets, chunk_size=1000):
        """
        Initialize the builder the framework.

        Args:
            sources([Store]): list of source stores
            targets([Store]): list of target stores
            chunk_size(int): chunk size for processing
        """
        self.sources = sources
        self.targets = targets
        self.chunk_size = chunk_size

        self.logger = logging.getLogger(type(self).__name__)
        self.logger.addHandler(logging.NullHandler())

    def connect(self):
        """
        Connect to the builder sources and targets.
        """
        stores = self.sources + self.targets
        for s in stores:
            s.connect()

    @abstractmethod
    def get_items(self):
        """
        Returns all the items to process.

        Returns:
            generator or list of items to process
        """
        pass

    def process_item(self, item):
        """
        Process an item. Should not expect DB access as this can be run MPI
        Default behavior is to return the item.
        Args:
            item:

        Returns:
           item: an item to update
        """
        return item

    @abstractmethod
    def update_targets(self, items):
        """
        Takes a dictionary of targets and items from process item and updates them
        Can also perform other book keeping in the process such as storing gridfs oids, etc.

        Args:
            items:

        Returns:

        """
        pass

    def finalize(self, cursor=None):
        """
        Perform any final clean up.
        """
        # Close any Mongo connections.
        for store in (self.sources + self.targets):
            try:
                store.collection.database.client.close()
            except AttributeError:
                continue
        # Runner will pass iterable yielded by `self.get_items` as `cursor`. If
        # this is a Mongo cursor with `no_cursor_timeout=True` (not the
        # default), we must be explicitly kill it.
        try:
            cursor and cursor.close()
        except AttributeError:
            pass

    def __getstate__(self):
        return self.as_dict()

    def __setstate__(self, d):
        del d["@class"]
        del d["@module"]
        md = MontyDecoder()
        d = md.process_decoded(d)
        self.__init__(**d)
