from libxmp.utils import file_to_dict

MAPPING = {
    'http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/': {'Iptc4xmpCore:Location': 'ID.INV', 
                                                    'Iptc4xmpCore:CreatorContactInfo/Iptc4xmpCore:CiAdrCity': 'LOCATION.ORIG',
                                                    'Iptc4xmpCore:CreatorContactInfo/Iptc4xmpCore:CiUrlWork': 'ID.CERL',
                                                    'Iptc4xmpCore:CreatorContactInfo/Iptc4xmpCore:CiAdrCtry': 'LOCATION.COUNTRY'},
    'http://purl.org/dc/elements/1.1/': {'dc:creator': 'CREATOR',
                                         'dc:description': 'DESCRIPTION', 
                                         'dc:subject': 'SUBJECT'},
}

def read_metadata(filepath):
    xmp = file_to_dict(filepath)
    record = {'filepath': filepath}
    for ns,v_list in xmp.items():
        for a,b,c in v_list:
            for field_name in MAPPING.get(ns, {}):
                if a.startswith(field_name) and b:
                    record.setdefault(MAPPING[ns][field_name], []).append(b)
    return record