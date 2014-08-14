import os
import math
from PIL import Image
import warnings

# Disable the warnings for giant images
warnings.simplefilter('ignore', Image.DecompressionBombWarning)

def clean(path):
    for f in os.listdir(path):
        if f.endswith('.jpg'):
            os.remove(os.path.join(path, f))

def calc_row_width_height(src):
    'For a given collection of files, calculate a good width and height for rows'
    file_collection = {}
    for x in os.listdir(src):
        if x.endswith('.jpg'):
            file_collection[x] = Image.open(os.path.join(src, x)).size

    count_per_row = int(round(math.sqrt(len(file_collection))))    
    average_width = sum(w for w,h in file_collection.values()) / len(file_collection)
    row_height = sum(h for w,h in file_collection.values()) / len(file_collection)
    row_width = count_per_row * average_width

    return row_width, row_height

def make_images_sameheight(src, dest, size=270):
    if not os.path.exists(dest):
        os.mkdir(dest)
    clean(dest)
    count = 0
    for filename in os.listdir(src):
        if not filename.endswith('.jpg') or filename.startswith('.'):
            continue
        img = Image.open(os.path.join(src, filename))
        w,h = img.size
        if h != size:            
            ratio = float(w)/float(h)
            new_w = int(size*ratio)
            new_img = img.resize((new_w, size), Image.ANTIALIAS)
            new_img.save(os.path.join(dest, filename))
        else:
            img.save(os.path.join(dest, filename))
        count += 1
    return count

def make_rows(src, dest, row_width, row_height):
    if not os.path.exists(dest):
        os.mkdir(dest)
    # Remove all .jpg files from dest
    clean(dest)

    f = [x for x in os.listdir(src) if x.endswith('.jpg')]
    f.sort()
    row = Image.new('RGBA', (row_width, row_height), color='white')
    row_idx = 0
    x = 0
    t_w = 0
    img = None
    while f or img:
        if not img:
            filename = f.pop(0)
            img = Image.open( os.path.join(src, filename))
            w,h = img.size
        if (t_w + w) < (row_width-(row_width*0.02)):
            if img.mode == 'RGBA':
                row.paste(img, (x,0), img)
            else:
                row.paste(img, (x,0))
            x += w
            t_w += w
            img = None
        else:
            if t_w > 0:
                crow = row.crop((0,0,t_w,row_height))
                crow.save(os.path.join(dest, '%.3d.jpg' % row_idx))
                row = Image.new('RGBA', (row_width, row_height), color='white')
                row_idx += 1
                t_w = 0
                x = 0
    if t_w > 0:
        crow = row.crop((0,0,t_w,row_height))
        crow.save(os.path.join(dest, '%.3d.jpg' % row_idx))

def make_by_rows(src, filename, row_width, row_height):
    rowfiles = sorted([x for x in os.listdir(src) if x.endswith('.jpg')])
    height_needed = len(rowfiles)*row_height
    big = Image.new('RGB', (row_width, height_needed), color='white')
    for row_idx, rowfile in enumerate(rowfiles):
        try:
            img = Image.open(os.path.join(src, rowfile))
        except IOError:
            raise Exception('Problem with', rowfile)
        w,h = img.size
        diff = row_width-w
        big.paste(img, (diff/2, row_idx*row_height))
    big.save(filename)
    return big
    
