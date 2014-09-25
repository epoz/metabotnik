import os
import math, random
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
            new_img.convert('RGB').save(os.path.join(dest, filename))
        else:
            img.convert('RGB').save(os.path.join(dest, filename))
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

def horzvert_layout(project):
    files = list(project.files.all())
    ROW_HEIGHT = min(f.height for f in files)

    # Calculate a new width/height for the files
    # based on making them all the same height
    # make_same_height
    for f in files:
        f.new_height = ROW_HEIGHT
        if f.height != ROW_HEIGHT:
            ratio = float(f.width)/float(f.height)
            f.new_width = int(ROW_HEIGHT*ratio)
        else:
            f.new_width = f.width

    # Given the files, how many should there be per row
    # and how wide should a row be?
    # calc_row_width_height
    count_per_row = int(round(math.sqrt(len(files))))
    average_width = sum(f.new_width for f in files) / len(files)
    row_height = sum(f.new_height for f in files) / len(files)
    row_width = count_per_row * average_width

    # Make the rows by calculating an offset for where the 
    # images should be placed
    new_files = []
    row_idx, rows = 0, []
    x,y = 0,0
    thefile = None
    cur_width = 0
    margin = row_width*0.98
    while files or thefile:
        if not thefile:
            thefile = files.pop(0) # just feels wrong to name it 'file'
            new_files.append(thefile)
        if (cur_width + thefile.new_width) < margin:
            thefile.x = x
            thefile.y = y
            thefile.row = row_idx            
            x += thefile.new_width
            cur_width += thefile.new_width
            thefile = None
        elif cur_width > 0:
            rows.append(cur_width)
            row_idx += 1
            cur_width = 0
            x = 0
            y += row_height

    if len(rows) < (row_idx+1):
        rows.append(cur_width)

    return new_files, rows, row_width, row_height

HTML = '''<canvas id="a" width="%(C_WIDTH)s" height="%(C_HEIGHT)s"></canvas>

<script type="text/javascript">
var canvas = document.getElementById("a");
var c = canvas.getContext("2d");
c.font = "96pt sans-serif";
c.fillStyle = "#eee";
c.fillRect(0,0,%(C_WIDTH)s,%(C_HEIGHT)s);

c.lineWidth = 2;
c.scale(%(scale_x)s, %(scale_y)s);
%(boxes)s

</script>
'''


def make_canvas(project):
    new_files, rows, row_width, row_height= horzvert_layout(project)

    # We need to know the amount to scale the canvas by
    # we have 500 x 500, and we need...
    C_WIDTH = 500.0
    C_HEIGHT = 500.0

    scale_x = C_WIDTH / row_width
    scale_y = C_HEIGHT / (row_height * len(rows))

    buf = []
    b = buf.append
    for f in new_files:
        # Each row is slightly less than the 'real' row_width
        # so we need to add a slight offset to the x position
        offset = (row_width - rows[f.row]) / 2        
        random_colour = '%x' % random.randint(0,180)
        b('c.fillStyle = "#%s";' % (random_colour*3))
        b('c.fillRect(%s,%s,%s,%s);' % (f.x+offset, f.y, f.new_width, f.new_height))
        b('c.strokeRect(%s,%s,%s,%s);' % (f.x+offset, f.y, f.new_width, f.new_height))
        b('c.fillStyle = "#fff";')
        b('c.fillText("%s", %s, %s);' % (f.filename, f.x+offset+100, f.y+(f.new_height/10)))
    tmp = HTML % {'C_WIDTH': C_WIDTH, 
                  'C_HEIGHT': C_HEIGHT, 
                  'scale_x': scale_x, 
                  'scale_y': scale_y,
                  'boxes': '\n'.join(buf) }

    return tmp