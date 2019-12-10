""" Contains classes to handle batch data components """
import copy as cp
import numpy as np
try:
    import pandas as pd
except ImportError:
    import _fake as pd

from .utils import is_iterable


class AdvancedDict(dict):
    """ dict that supports advanced indexing """
    def __getitem__(self, item):
        if isinstance(item, (list, np.ndarray)):
            d = type(self)()
            for i in item:
                d[i] = self[i]
            return d
        return super().__getitem__(item)

    def as_array(self, indices=None):
        """ Return data as an array """
        if indices is None:
            indices = self.keys()
        return np.stack([self[i] for i in indices])

class BaseComponents:
    """ Base class for a components storage """
    def __init__(self, components=None, data=None, indices=None, crop=False, copy=False, cast_to_array=True):
        self.components = components
        self._indices = indices
        self.data = data
        self.cast_to_array = cast_to_array
        self._crop = crop
        if crop:
            self.crop()
        if copy:
            self.data = cp.deepcopy(self.data)

    def crop(self, indices=None):
        """ Crops from data in accordance with indices """
        indices = indices if indices is not None else self._indices
        if isinstance(self.data, pd.DataFrame):
            self.data = self.data.loc[indices]
        elif self.components is not None:
            new_data = {}
            for comp in self.components:
                # if isinstance(self.data, BaseComponents):
                #     comp_data = self.data.get(comp, indices)
                # else:
                #     comp_data = self.data.get(comp)[indices]
                comp_data = self._get(comp, indices)
                new_data[comp] = comp_data
            self.data = new_data

    @property
    def indices(self):
        return None if self._crop else self._indices

    def __str__(self):
        s = str(type(self)) + ':\n'
        if self.components is not None:
            for comp in self.components:
                d = getattr(self, comp, None)
                s += '  ' + comp + ': ' + str(d) + '\n'
        if self.indices is not None:
            s += 'indices: ' + str(self.indices) + '\n'
        #s += '  data: ' + str(self.data) +'\n'
        return s

    def as_list(self, components=None):
        """ Return components data as a tuple """
        comps = components
        if isinstance(components, str):
            components = (components, )
        components = tuple(components or self.components)

        res = [getattr(self, comp) for comp in components]

        return res[0] if isinstance(comps, str) else res

    def as_tuple(self, components=None):
        """ Return components data as a tuple """
        return tuple(self.as_list(components))

    def as_dict(self, components=None):
        """ Return components data as a dict """
        if isinstance(components, str):
            components = (components, )
        components = tuple(components or self.components)
        return dict(zip(components, self.as_tuple(components)))

    def as_array(self, components=None):
        """ Return a component as an array """
        comps = self.as_list(components)
        return comps.as_array(self._indices)

    def __len__(self):
        return len(self.data)

    # def __add__(self, other):
    #     if not isinstance(other, tuple):
    #         raise TypeError("Tuple is expected, while got %s" % type(other))
    #     self.data = self.data + other

    def __getitem__(self, item):
        if isinstance(item, slice):
            item = list(range(item.start, item.stop, item.step))
        if self.components is None:
            return self._get(item)
        if self._indices is not None and item not in self._indices:
            raise KeyError(item)
        return type(self)(self.components, self, item, crop=False)

    def find_in_index(self, item):
        if isinstance(self._indices, list):
            return self._indices.index(item)
        if isinstance(self._indices, np.ndarray):
            it = np.where(self._indices == item)[0][0]
            return it
        raise TypeError("Unknown index type: %s" % type(self._indices))

    def get_pos(self, component, indices):
        """ Return positions of given indices """
        if self._indices is not None:
            # a cropped numpy array needs a position as an index
            if isinstance(self.data[component], np.ndarray):
                if is_iterable(indices):
                    items = [self.find_in_index(i) for i in indices]
                else:
                    items = self.find_in_index(indices)
            else:
                items = indices
        else:
            items = indices
        return items

    def _get(self, component, indices=None):
        indices = indices if indices is not None else self._indices
        if self.data is None:
            return None
        if isinstance(self.data, BaseComponents):
            return self.data.get(component, indices)
        data = self.data.get(component, None)
        if data is None:
            return None
        if indices is not None:
            items = self.get_pos(component, indices)
            if isinstance(data, dict):
                return AdvancedDict(data)[items]
            return data[items]
        return data

    def get(self, component, indices=None):
        """ Returns a value of a component with indices given """
        data = self._get(component, indices)

        if self.cast_to_array:
            if isinstance(data, pd.Series): # and np.all(data.index == self.indices):
                data = data.values
            elif isinstance(data, AdvancedDict):
                data = data.as_array(self.indices)
        return data

    def set(self, component, indices, value):
        """ Assign a value to a component with indices given """
        if self.data is None:
            self.data = {}
        if isinstance(self.data, BaseComponents):
            self.data.set(component, indices or self._indices, value)
        elif indices is not None:
            items = self.get_pos(component, indices)
            self.data[component][items] = value
        else:
            self.data[component] = value

    def __getattr__(self, name):
        if self.components is None and self.data is not None:
            return getattr(self.data, name)
        if name in self.components:
            return self.get(name, self.indices)

    def __setattr__(self, name, value):
        if name in ('data', 'components'):
            super().__setattr__(name, value)
        elif self.components is not None and name in self.components:
            self.set(name, self.indices, value)
        else:
            super().__setattr__(name, value)


def _get_crop(source, indices):
    return source[indices] if source is not None else None

def get_from_source(components=None, data=None, indices=None, crop=False, copy=False, cast_to_array=True):
    """ Return data source (and make a crop and a copy if necessary) """
    _ = components, crop, cast_to_array

    source = data
    if indices is not None:
        if isinstance(source, (list, tuple)):
            data = type(source)([_get_crop(item, indices) for item in source])
        elif isinstance(source, dict):
            data = [_get_crop(source[item], indices) for item in source]
            data = dict(zip(source.keys(), data))
        else:
            if isinstance(source, pd.DataFrame):
                data = source.loc
            print(data, indices)
            data = _get_crop(data, indices)

    if copy and data is not None:
        data = cp.deepcopy(data)

    return data


def create_item_class(components, source=None, indices=None, crop=None, copy=False, cast_to_array=True):
    """ Create components class """
    item_class = BaseComponents
    if components is not None:
        # source is an object supporting double-indexing `source[component][item_index]`
        # so it can be a tuple, dict, pd.DataFrame, etc
        if isinstance(source, (list, tuple)):
            source = dict(zip(components, source))
    else:
        # source is a memory-like object (ndarray, hdf5 storage, etc)
        item_class = get_from_source

    item = item_class(components, data=source, indices=indices, crop=crop, copy=copy, cast_to_array=cast_to_array)

    return item
