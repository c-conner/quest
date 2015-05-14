"""NRMM Filter

"""

from .base import FilterBase
from ..api import get_collection, add_to_collection
from .. import util
from geojson import Polygon, Feature, FeatureCollection
import numpy as np
import os
import subprocess
import time


class NrmmFromVITD(FilterBase):
    def register(self):
        """Register VITD to NRMM Filter

        """
        self.schema = {}

        self.metadata = {
            'operates_on': {
                'datatype': ['terrain-vitd'],
                'geotype': ['polygon'],
                'parameters': ['terrain-nrmm'],
                'level': ['collection'],
            },
            'produces': {
                'datatype': 'terrain-nrmm',
                'geotype': 'polygon',
                'parameters': 'nrmm',
            },
        }


    def apply_filter(self, collection_name, **kwargs):
        available_themes = self.get_themes().keys()

        themes = []
        for k, v in kwargs.items():
            if k in available_themes:
                if v:
                    themes.append(k)

        themes = ' '.join(themes)
        collection = get_collection(collection_name)

        #calculate bounding box
        locations = collection['datasets']['iraq-vitd']['locations']['features']
        locs = np.hstack([loc['geometry']['coordinates'] for loc in locations]).squeeze()
        lons = locs[:,0]
        lats = locs[:,1]
        south, north = lons.min(), lons.max()
        west, east = lats.min(), lats.max()
        bounding_box = ','.join([str(n) for n in [south, west, north, east]])
        
        nrmm_id = 'nrmm-%s' % (bounding_box)
        plugin_dir = os.path.join(collection['path'], 'vitd2nrmm')
        util.mkdir_if_doesnt_exist(plugin_dir)
        #dest = 'nrmm/data-%s.dat' % nrmm_id
        nrmm_file = 'vitd2nrmm/NRMM/NRMM.grd'
        #open(os.path.join(collection['path'], dest), 'w').close() #make fake empty file
        properties = {'metadata': 'generated using vitd2nrmm plugin', 'relative_path': nrmm_file}
        new_locs = FeatureCollection([Feature(geometry=Polygon([util.bbox2poly(south, west, north, east)]), properties=properties, id=nrmm_id)])
        path = collection['path']        
        vitd_dir = os.path.join(path, 'nga/iraq/vitd')
        #call plugin.
        print 'calling VITD to NRMM plugin for bounding box - %s, with themes - %s' % (bounding_box, themes)
        args = [
            'vitd2nrmm',
            '-i', '"%s"' % vitd_dir,
            '-o', '"%s"' % plugin_dir,
            '-n', str(north),
            '-s', str(south),
            '-e', str(east),
            '-w', str(west),
        ]

        if len(themes) > 0:
            args += ['-t', themes]

        resolution = kwargs.get('resolution')
        if resolution is not None:
            args += ['-r', str(resolution)]

        print '--> %s' % (' '.join(args))
        try:
            subprocess.call(' '.join(args))
            print 'success'
            print 'nrmm file written to: %s' % os.path.join(path, nrmm_file)
            collection = add_to_collection(collection_name, 'local', new_locs, parameters='terrain-nrmm')
        except:
            print 'plugin call failed'

        return collection

    def apply_filter_options(self, **kwargs):
        themes = self.get_themes()
        properties = {
            "collection_name": {
                "type": "string",
                "description": "Name of collection",
            }, 
        }
        for k, v in themes.iteritems():
            properties.update({
                    k: {
                        "type": "boolean",
                        "description": v,    
                    } 
                })

        properties.update({"resolution": {"type": { "enum": [ 1, 2, 3, 4, 5 ], "default": 5 },
                                          "description": "resolution of output"}})

        schema = {
            "title": "Download Options",
            "type": "object",
            "properties": properties,
            "required": ["collection_name"],
        }
        
        return schema

    def get_themes(self): #, filename):
        #with open(filename) as f:
        #    s = filter(lambda x: x in string.printable, f.read())
        #
        #s = s.split(';')[-1]
        #return {s[x:x+58][:3]:s[x:x+58][3:].strip() for x in range(0, len(s), 58)}
        themes = {
            'obs': 'Obstacles',
            'sdr': 'Surface Drainage',
            'slp': 'Slope/Surface Configuration',
            'smc': 'Soils/Surface Materials',
            'trn': 'Transportation',
            'veg': 'Vegetation'
        }

        return themes