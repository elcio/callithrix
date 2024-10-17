import os
import re
import glob
import shutil
import asyncio
from fastapi import Request
from callithrix import SubApp
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask


class ImageServerApp(SubApp):

    async def save_image(self, fileobj, filename):
        if re.match(r'^\d+\.\d+-\w+_\d+_\w+\.\w+$', filename):
            self.remove_db_image(filename)
        original = abs_path() + '/original/' + filename

        with open(original, 'wb') as f:
            f.write(await fileobj.read())

        return path

    def remove_db_image(self, filename):
        filename = '*.*-' + filename.split('-')[-1]
        original = glob.glob(abs_path() + '/original/' + filename)
        optimized = glob.glob(abs_path() + '/optimized/' + filename + '.avif')
        thumbs_original = glob.glob(abs_path() + '/original/thumb/*x*_' + filename)
        thumbs_optimized = glob.glob(abs_path() + '/optimized/thumb/*x*_' + filename + '.avif')
        for thumb in original + optimized + thumbs_original + thumbs_optimized:
            self.remove_file(thumb)
        return path

    def remove_file(self, path):
        if os.path.exists(path):
            os.remove(path)


app = ImageServerApp(globals())
path = '/images/'
tasks = []


def init(imagespath=None):
    global path
    if imagespath:
        path = imagespath
    os.makedirs(abs_path() + '/original/thumb', exist_ok=True)
    os.makedirs(abs_path() + '/optimized/thumb', exist_ok=True)


async def optimize(original, optimized):
    if original not in tasks:
        if not os.path.exists(optimized+'_temp.avif'):
            tasks.append(original)
            if original.endswith('.gif'):
                proc = await asyncio.create_subprocess_shell(
                    f'ffmpeg -hide_banner -i {original} -c:v libsvtav1 -crf 30 -preset 4 -pix_fmt yuv420p10le -svtav1-params tune=0 -y {optimized}_temp.avif',
                    stdout=asyncio.subprocess.PIPE)
            else:
                proc = await asyncio.create_subprocess_shell(
                    f'convert {original} -quality 50% {optimized}_temp.avif',
                    stdout=asyncio.subprocess.PIPE)
            await proc.communicate()
            shutil.move(f'{optimized}_temp.avif', optimized)
            tasks.remove(original)

def abs_path():
    return path.removeprefix('/').removesuffix('/')

@app.gethtml('/{img}')
async def server_image(request: Request, img: str):
    original = abs_path() + '/original/' + img
    optimized = abs_path() + '/optimized/' + img + '.avif'
    return await serve_image(original, optimized)


async def serve_image(original, optimized):
    if os.path.exists(optimized):
        return FileResponse(optimized)
    elif os.path.exists(original):
        if original in tasks:
            return FileResponse(original)
        task = BackgroundTask(optimize, original, optimized)
        return FileResponse(original, background=task)
    else:
        return {'404': original.split('/')[-1]}


@app.gethtml('/{width}x{height}/{img}')
async def resized_image(request: Request, width: int, height: int, img: str):
    if width > 6000 or height > 6000:
        prop = 6000 / max(width, height)
        width = int(width * prop)
        height = int(height * prop)
    original = abs_path() + '/original/' + img
    resized = abs_path() + f'/original/thumb/{width}x{height}_{img}'
    optimized = abs_path() + f'/optimized/thumb/{width}x{height}_{img}.avif'
    if not os.path.exists(resized):
        proc = await asyncio.create_subprocess_shell(
            f'convert {original} -gravity Center -extent {width}:{height} -resize {width}x{height} {resized}',
            stdout=asyncio.subprocess.PIPE)
        await proc.communicate()
    return await serve_image(resized, optimized)

