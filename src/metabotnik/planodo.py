import os
import math, random
from PIL import Image
import warnings
import json
from django.db import connection

# Disable the warnings for giant images
warnings.simplefilter('ignore', Image.DecompressionBombWarning)

class Last:
    pass

def phorzvert_layout(project, frame=None):
    # sort the images by size, largest first where size is the area    
    files = sorted(project.files.all(), key=lambda x: x.width * x.height, reverse=True)
    last_file = Last()
    last_file.x, last_file.y = 0, 0
    last_file.width, last_file.height = 0,0
    order = ['t', 'r', 'b', 'l']  # top, right, bottom, left
    canvas_width, canvas_height = 0, 0
    new_files = []
    while files:
        file = files.pop()
        if not order:
            order = ['t', 'r', 'b', 'l']

        new_order = order.pop(0)
        if new_order == 't':
            file.x = last_file.x
            file.y = last_file.y - file.height
            last_file.y -= file.height
        elif new_order == 'r':
            file.x = last_file.x + last_file.width
            file.y = last_file.y            
        elif new_order == 'b':
            file.x = last_file.x
            file.y = last_file.y + last_file.height
        elif new_order == 'l':
            file.x = last_file.x - file.width
            file.y = last_file.y
            last_file.x -= file.width
        if new_order in ('t', 'b'):
            last_file.height += file.height
        if new_order in ('r', 'l'):
            last_file.width += file.width
        new_files.append(file)

    # And save all the modified attributes
    for f in new_files:
        f.new_width, f.new_height = f.width, f.height
        cursor = connection.cursor()
        cursor.execute('UPDATE metabotnik_file SET x = %s, y = %s, new_width = %s, new_height = %s WHERE id = %s',
                       (f.x, f.y, f.new_width, f.new_height, f.pk))
    project.metabotnik_width = last_file.width
    project.metabotnik_height = last_file.height
    project.save()

def horzvert_layout(project, frame=0):
    '''Do the layout and produce a usable dict output that can be persisted with the Project.
    We used to save these as attributes in the File objects.
    '''
    # Allow overrriding the row_height by having a paramater passed in
    files = list(project.files.all())

    if project.layout_mode == 'horizontal':
        stripe_height = min(f.height for f in files)
        if frame == 'slide':
            frame = stripe_height / 2
            stripe_height += frame*2
    if project.layout_mode == 'vertical':
        stripe_width = min(f.width for f in files)
        if frame == 'slide':
            frame = stripe_width / 2
            stripe_width += frame*2

    # If a frame was passed in, adjust the x,y of all items to give them that much spacing as a frame
    try:
        frame = int(frame)
    except ValueError:
        frame = 0    


    # Calculate a new width/height for the files
    # based on making them all the same height
    for f in files:
        if project.layout_mode == 'horizontal':
            f.new_height = stripe_height
            if f.height != stripe_height:
                ratio = float(f.width)/float(f.height)
                f.new_width = int(stripe_height*ratio)
            else:
                f.new_width = f.width
        elif project.layout_mode == 'vertical':
            f.new_width = stripe_width
            if f.width != stripe_width:
                ratio = float(f.height)/float(f.width)
                f.new_height = int(stripe_width*ratio)
            else:
                f.new_height = f.height
        else:
            f.new_width = f.width
            f.new_height = f.height

    # Given the files, how many should there be per row
    # and how wide should a row be?
    # calc_row_width_height
    count_per_stripe = int(round(math.sqrt(len(files))))
    average_width = sum(f.new_width for f in files) / len(files)
    average_height = sum(f.new_height for f in files) / len(files)

    if project.layout_mode == 'horizontal':
        stripe_size = count_per_stripe * (average_width+frame*count_per_stripe)
        stripe_width = stripe_size
    elif project.layout_mode == 'vertical':
        stripe_size = count_per_stripe * (average_height+frame*count_per_stripe)
        stripe_height = stripe_size        
    else:
        stripe_size = count_per_stripe * average_height
        stripe_width = stripe_height = stripe_size

    # Make the stripes by calculating an offset for where the 
    # images should be placed
    new_files = []
    stripe_idx, stripes = 0, []
    x,y = 0,0
    thefile = None
    cur_size = 0
    if len(files) == 1:
        margin = stripe_size+1
    else:
        margin = stripe_size*0.965
    while files or thefile:
        if not thefile:
            thefile = files.pop(0) # just feels wrong to name it 'file'
            new_files.append(thefile)        
        if project.layout_mode == 'horizontal':
            if (cur_size + thefile.new_width) < margin:
                thefile.x = x
                thefile.y = y
                thefile.stripe = stripe_idx            
                x += thefile.new_width
                cur_size += thefile.new_width
                dontfit = True if thefile.is_break else False
                thefile = None
                x += frame
            else:
                dontfit = True
            if dontfit and (cur_size > 0):
                stripes.append(cur_size)
                stripe_idx += 1
                cur_size = 0
                x = 0
                y += stripe_height
                y += frame
        elif project.layout_mode == 'vertical':
            if ((cur_size + thefile.new_height) < margin):
                thefile.x = x
                thefile.y = y
                thefile.stripe = stripe_idx            
                y += thefile.new_height
                cur_size += thefile.new_height
                dontfit = True if thefile.is_break else False
                thefile = None
                y += frame                
            else:
                dontfit = True
            if dontfit and (cur_size > 0):
                stripes.append(cur_size)
                stripe_idx += 1
                cur_size = 0
                y = 0
                x += stripe_width
                x += frame
        else:
            thefile.x = random.randint(0, stripe_width-thefile.width)
            thefile.y = random.randint(0, stripe_height-thefile.height)
            thefile = None


    if len(stripes) < (stripe_idx+1):
        stripes.append(cur_size)
    
    if project.layout_mode == 'horizontal':
        # In horizontal project.layout_mode, each stripe has an actual width that is less than the stripe_width
        # To make the layout nicely centered, adjust each x with an offset.
        for f in new_files:
            offset = (stripe_width - stripes[f.stripe]) / 2
            f.x = f.x+offset
        canvas_width = stripe_width
        canvas_height = stripe_height * len(stripes)
    elif project.layout_mode == 'vertical':
        for f in new_files:
            offset = (stripe_height - stripes[f.stripe]) / 2
            f.y = f.y+offset
        canvas_width = stripe_width * len(stripes)
        canvas_height = stripe_height
    else:
        canvas_width = stripe_width
        canvas_height = stripe_height

    data = {
        'version':1, 
        'width': canvas_width, 
        'height': canvas_height,
        'background_color': project.background_color,
        'images': []
    }

    # And save all the modified attributes
    for f in new_files:
        random_colour = '%x' % random.randint(0,180)
        tmp = { 'pk':f.pk, 'filename':f.filename, 'fill_style': '#%s' % (random_colour*3),
                'x': f.x, 
                'y': f.y, 
                'width': f.new_width, 
                'height': f.new_height,
                'metadata': f.metadata and json.loads(f.metadata) or {},
        }
        data['images'].append( tmp )

    return data

def make_bitmap(project, filepath):
    'Given the layout coordinates for @project, generate a bitmap and save it under @filename'
    # Make the gigantic bitmap, if it is too large try and scale down the size using horzvert_layout iteratively
    MAX_WIDTH= 65000
    MAX_HEIGHT = 65000

    layout_data = project.layout_as_dict()


    if layout_data['width'] > 65000:
        raise Exception('Width %s is > %s' % (layout_data['width'], MAX_WIDTH))
    if layout_data['height'] > 65000:
        raise Exception('Height %s is > %s' % (layout_data['height'], MAX_HEIGHT))

    msgs = []
    large = Image.new('RGBA', (layout_data['width'], layout_data['height']), color=layout_data['background_color'])
    for f in layout_data.get('images', []):
        try:
            img = Image.open(os.path.join(project.originals_path, f['filename']))
            i_width, i_height = img.size
            if i_width != f['width'] or i_height != f['height']:
                img = img.resize((f['width'], f['height']), Image.ANTIALIAS)
        except IOError:
            msgs.append('Problem with %s' % f['filename'])
            continue
        if img.mode == 'RGBA':
            large.paste(img, (f['x'], f['y']), img)
        else:
            large.paste(img, (f['x'], f['y']))
    large.save(filepath)

    return msgs