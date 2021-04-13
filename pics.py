# pics.py
# developed by Nick Lockhart
# Apr 2021

from aiohttp import web
from pathlib import Path
from PIL import Image
from fractions import Fraction
import os
import io
import urllib
import datetime
import exif

parse_quote = urllib.parse.quote

routes = web.RouteTableDef()

sidebar = """<div class='body-sidebar'>
    <p><img src="/logo" alt="Generic photo icon" class="img-no-overflow"></p>
    <p><a href="/pics/">Home</a></p>
    <p><a href="/upload">Upload</a></p>
    <p><a href="/manage">Manage</a></p>
</div>
"""

def is_photo(file_path):
    try:
        Image.open(file_path)
        return True
    except:
        return False

def date_name_split(ds_input: str, whitespace_char='_'):
    """Split a folder name (or arbitrary string) into a date, an album name, and the raw input.
    Returns a list containing a datetime.date object, the name as a string, and the raw input as a string, in that order."""
    ds_temp = [ds_input.split(whitespace_char)[0], ' '.join(ds_input.split(whitespace_char)[1:])]
    if len(ds_temp[0]) < 10 or not (ds_temp[0][4] == '-' and ds_temp[0][7] == '-'):
        ds_temp[1] = f"{ds_temp[0]} {ds_temp[1]}"
        ds_date = datetime.date.min
    else:
        ds_date = datetime.date.fromisoformat(ds_temp[0])
    return [ds_date, ds_temp[1], ds_input]

def generate_clickable_path(path_in: str):
    """Generate the HTML for a clickable path for navigation."""
    
    path_split = [x for x in path_in.split('/') if x != '']

    full_html = "<p><b>Path:</b> /"
    for x in range(0, len(path_split)):
        next_component = '/'.join(path_split[:x] + [path_split[x]])
        if x == len(path_split) - 1 and len(path_split) > 1:
            full_html += f"<a href='/{next_component}'>{path_split[x]}</a>"
        else:
            full_html += f"<a href='/{next_component}/'>{path_split[x]}</a>/"
    full_html += "</p>"

    return full_html

def generate_file_html(filename, url):
    response = f"""
    <div class='photo'>
        <a href=/pics{url}><img src="/scale/{url}" alt="{filename}" class="img-photo"></a>
        <div class='caption-photo'>
            <a href="/pics{url}">{filename}</a><br>
            {get_file_info_string(f"./pics/{url}")}
        </div>
    </div>
    """
    return response

def get_file_info_string(file_path):
    """Generate a file information string.
    If an image is found at the path, return size and height.
    Otherwise, return just the filesize."""

    info_string = "Catastrophic failure!"
    
    if os.path.isdir(file_path):
        info_string = "Folder (wtf?)"
    else:
        # this is not a magic number - 1024*1024 / bytes to mb
        filesize_mb = round(os.path.getsize(file_path) / 1048576, 2)
        try:
            image_obj = Image.open(file_path)
            w, h = image_obj.size
            info_string = f"{filesize_mb}mb ({w}x{h})"
        except:
            info_string = f"{filesize_mb}mb"
    return info_string



def generate_photo_container(req_path_in: str, files_in: list):
    "Generate a photo-container div based on the files in a folder and a request path."
    html_out = "<div class='photo-container'>\n"
    for filename in files_in:
        next_element = generate_file_html(filename, f"/{req_path_in.strip('/')}/{parse_quote(filename)}")
        html_out += next_element + '\n'
    html_out += "</div>"
    return html_out
    # ''.join(generate_file_html(filename, f"{request_path}/{parse_quote(filename)}") for filename in files)

def generate_folder_groups(req_path_in: str, folders_in: list):
    
    folders_in.sort(reverse=True)
    response = "<div class='folder-groups'>\n"
    dates_names = [date_name_split(folder_name) for folder_name in folders_in]

    album_groups = {}
    for dn_pair in dates_names:
        pair_date = dn_pair[0]
        if pair_date.year not in album_groups:
            album_groups[pair_date.year] = []
        album_groups[pair_date.year].append(dn_pair)

    years = [year for year in album_groups.keys()]
    years.sort(reverse=True)
    for year in years:
        response += "<div class='folder-group-container'>\n"
        if year == datetime.MINYEAR:
            response += "<p class='folder-caption'><b>Unsorted</b></p>\n"
            response += "<div class='folder-group'>\n"
            response += "<ul class='folder-list'>\n"
            for event in album_groups[year]:
                if req_path_in == '':
                    response += f"<li><a href='/pics/{event[2]}'>{event[1]}</a></li>\n"
                else:
                    response += f"<li><a href='/pics/{req_path_in}/{event[2]}'>{event[1]}</a></li>\n"
            response += "</ul>"
            response += "</div>"
        else:
            response += f"<p class='folder-caption'><b>{year}</b></p>"
            response += "<div class='folder-group'>\n"
            response += "<ul class='folder-list'>\n"
            for event in album_groups[year]:
                if req_path_in == '':
                    response += f"<li><a href='/pics/{event[2]}'>{event[0].strftime('%d %b')}: {event[1]}</a></li>\n"
                else:
                    response += f"<li><a href='/pics/{req_path_in}/{event[2]}'>{event[0].strftime('%d %b')}: {event[1]}</a></li>\n"
            response += "</ul>"
            response += "</div>"
        response += "</div>"
    response += "</div>"
    return response

def generate_exif_table(path_in: str, req_path_in: str, extended_info = False):
    "Try to generate a HTML table for the EXIF data in an image; return an error message if an error occurs"
    try:
        with open(path_in, 'rb') as im_file:
            im_exif = exif.Image(im_file)
        if not im_exif.has_exif:
            return "<p>No EXIF data is available for this image.</p>" # no exif data; don't show a table
        else:
            response = "<table class='exif-table'>"
            response += "<tr><th class='exif-table-header' colspan=2>Image info</th></tr>"
            if extended_info:
                for exif_tag in im_exif.list_all():
                    if exif_tag[0] == '_':
                        pass # not useful for our purposes
                    elif exif_tag == 'flash':
                        exif_data_for_tag = im_exif.get(exif_tag)
                        if exif_data_for_tag.flash_fired:
                            response += f"<tr><td class='exif-table'><b>{exif_tag}:</b></td><td class='exif-table'>Flash fired</td></tr>\n"
                        else:
                            response += f"<tr><td class='exif-table'><b>{exif_tag}:</b></td><td class='exif-table'>Flash was not fired</td></tr>\n"

                    else:
                        exif_data_for_tag = im_exif.get(exif_tag)
                        response += f"<tr><td class='exif-table'><b>{exif_tag}:</b></td><td class='exif-table'>{exif_data_for_tag}</td></tr>\n"
                response += "</table>"
            else:
                short_tags = (('Camera manufacturer', 'make'),
                ('Camera model', 'model'),
                ('Exposure', 'exposure_time'),
                ('Aperture','f_number'),
                ('Focal length', 'focal_length'),
                ('ISO', 'photographic_sensitivity'),
                ('Flash', 'flash'),
                ('Date taken', 'datetime_original'))
                data = [[tag_group[0], im_exif.get(tag_group[1])] for tag_group in short_tags]
                for data_element in data:
                    if isinstance(data_element[1], exif.Flash):
                        if data_element[1].flash_fired:
                            response += f"<tr><td class='exif-table'><b>{data_element[0]}:</b></td><td class='exif-table'>Flash fired</td></tr>\n"
                        else:
                            response += f"<tr><td class='exif-table'><b>{data_element[0]}:</b></td><td class='exif-table'>Flash was not fired</td></tr>\n"
                    elif data_element[0] == "Exposure":
                        nice_exposure = Fraction(data_element[1]).limit_denominator()
                        response += f"<tr><td class='exif-table'><b>{data_element[0]}:</b></td><td class='exif-table'>{nice_exposure} sec</td></tr>\n"
                    else:
                        response += f"<tr><td class='exif-table'><b>{data_element[0]}:</b></td><td class='exif-table'>{data_element[1]}</td></tr>\n"
                response += "</table>"
                response += f"<a href=/pics/{req_path_in}?exif=1>Get more info</a>"

            return response
    except Exception as e:
        response = "<p><i>An error occured whilst obtaining EXIF data for this image.</i></p>"
        response += f"<code>{e}</code>"
        return response
        
@routes.get('/css')
async def css(request):
    with open('./main.css', 'r') as cssfile:
        css = cssfile.read()
    return web.Response(text=css, content_type='text/css')

@routes.get(r'/pics/{request_path:.*}')
async def pics_handler(request):
    request_path = request.match_info['request_path']
    fs_path = f"./pics/{request_path}"
    if os.path.isfile(fs_path):
        if is_photo(fs_path):
            if 'dl' in request.rel_url.query and request.rel_url.query['dl'] == '1':
                with open(fs_path, 'rb') as img_file_obj:
                    img_data = img_file_obj.read()
                return web.Response(body=img_data, content_type="application/octet-stream")
            else:
                if 'exif' in request.rel_url.query and request.rel_url.query['exif'] == '1':
                    request_extended_exif = True
                else:
                    request_extended_exif = False
                response = f"""<!DOCTYPE HTML>
<html>
    <head><link rel='stylesheet' href='/css'></head>
    <body>
        <div class='body-container'>
            {sidebar}
            <div class='body-main-content'>
                {generate_clickable_path(f"/pics/{request_path}")}
                <p><img src='/scale/{request_path}?height=512' class='image-preview'></p>
                <p><a href='/pics/{request_path}?dl=1'>Download original</a></p>
                {generate_exif_table(fs_path, request_path, extended_info=request_extended_exif)}
            </div>
        </div>
    </body>
</html>
                """
                return web.Response(text=response, content_type="text/html")
        else:
            with open(fs_path, 'rb') as file_obj:
                file_data = file_obj.read()
            return web.Response(body=file_data, content_type="application/octet-stream")

    elif os.path.isdir(fs_path):
        folder_entries = os.listdir(fs_path)
        files = []
        subfolders = []
        for entry in folder_entries:
            fullpath = f"{fs_path}/{entry}"
            if os.path.isfile(fullpath):
                files.append(entry)
            elif os.path.isdir(fullpath):
                subfolders.append(entry)
        if len(files) == 0 and len(subfolders) == 0:
            response = f"""<!DOCTYPE HTML>
<html>
    <head><link rel='stylesheet' href='/css'></head>
    <body>
        <div class='body-container'>
            {sidebar}
            <div class='body-main-content'>
                {generate_clickable_path(f"/pics/{request_path}")}
                <p>This folder is empty.</p>
            </div>
        </div>
    </body>
</html>
            """
        else:
            response = f"""<!DOCTYPE HTML>
<html>
    <head><link rel='stylesheet' href='/css'></head>
    <body>
        <div class='body-container'>
            {sidebar}
            <div class='body-main-content'>
                {generate_clickable_path(f"/pics/{request_path}")}
                {generate_folder_groups(request_path, subfolders )}
                {generate_photo_container(request_path, files)}
            </div>
        </div>
    </body>
</html>
            """
        return web.Response(text=response, content_type="text/html")
    else:
        response = f"""<!DOCTYPE HTML>
<html>
    <head><link rel='stylesheet' href='/css'></head>
    <body>
        <div class='body-container'>
            {sidebar}
            <div class='body-main-content'>
                {generate_clickable_path(f"/pics/{request_path}")}
                <p>The path you have requested does not exist.</p>
            </div>
        </div>
    </body>
</html>
        """
        return web.Response(text=response, content_type="text/html", status=404)

@routes.get(r'/logo')
async def logo(request):
    with open('./assets/logo.png', 'rb') as logofile:
        logodata = logofile.read()
    return web.Response(body=logodata, content_type="image/png")

@routes.get(r'/scale/{request_path:.*}')
async def scale_handler(request):
    usr_request_path = f"./pics/{request.match_info['request_path']}"
    if 'height' in request.rel_url.query:
        req_height = request.rel_url.query['height']
        baseheight = int(req_height) if req_height.isdigit() else 256
    else:
        baseheight = 256

    try:
        image_obj = Image.open(usr_request_path)
    except:
        image_obj = Image.open('./assets/file.png')
    
    wpercent = baseheight / float(image_obj.size[1])
    wsize = int(float(image_obj.size[0]) * float(wpercent))
    img_ret = image_obj.resize((wsize, baseheight), Image.ANTIALIAS)

    img_ret_arr = io.BytesIO()
    img_ret.save(img_ret_arr, format='PNG')
    return web.Response(body=img_ret_arr.getvalue(), content_type="image/png")



app = web.Application()
app.add_routes(routes)
web.run_app(app)