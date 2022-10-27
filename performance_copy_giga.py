# pip install anyio aiofile aiofiles
import asyncio
import random
from aiofile import async_open
import aiofiles
import aiofiles.os
import anyio
from anyio.streams.file import FileReadStream, FileWriteStream
import time
from typing import Coroutine
from contextlib import contextmanager
from tempfile import TemporaryDirectory, NamedTemporaryFile
from string import ascii_letters, punctuation


@contextmanager
def meas_time(name: str):
    start = time.perf_counter()
    start_process = time.process_time()
    try:
        yield
    finally:
        print(f"{name}:", time.perf_counter() - start, "[s]")
        print(f"{name}(Process):", time.process_time() - start_process, "[s]")


async def io_test(copy_func: Coroutine, src_file: anyio.Path):
    with TemporaryDirectory() as tmp_dir:
        dest_file = anyio.Path(tmp_dir) / "dest_file"

        print("2 seconds sleep...\n")
        await asyncio.sleep(2)
        print("start copy test")
        with meas_time(copy_func.__name__):
            await copy_func(src_file, dest_file)
        print("end copy test\n")


async def run_copy_test():

    async def wait_copy():
        await asyncio.sleep(random.uniform(0, 1))

    
    with NamedTemporaryFile() as fp:
        # anyio
        src_file = anyio.Path(fp.name)
        char_to_file = bytes(random.choice(ascii_letters + punctuation), 'utf-8')
        async with await FileWriteStream.from_path(src_file) as dest:
        # create 1GB file
            await dest.send(char_to_file * (1024 * 1024 * 1024))
        
        
        # anyio
        async def anyio_copy(src_file, dest_file):
            await wait_copy()
            async with await FileReadStream.from_path(src_file) as src_file, await FileWriteStream.from_path(dest_file) as dest_file:
                async for chunk in src_file:
                    await dest_file.send(chunk)

        await io_test(anyio_copy, src_file)
        
        
        # aiofiles      
        async def aiofiles_copy(src_file, dest_file):
            await wait_copy()
            stat_src = await aiofiles.os.stat(src_file)
            async with aiofiles.open(src_file, mode='rb') as src, aiofiles.open(dest_file, mode='wb') as dest:
                n_bytes = stat_src.st_size
                fd_src = src.fileno()
                fd_dst = dest.fileno()
                await aiofiles.os.sendfile(fd_dst, fd_src, 0, n_bytes)
                
        await io_test(aiofiles_copy, src_file)
        

        # aiofile
        async def aiofile_copy(src_file, dest_file):
            await wait_copy()
            async with async_open(str(src_file), "rb") as src, async_open(str(dest_file), "wb") as dest_file:
                async for chunk in src.iter_chunked(32768):
                    await dest_file.write(chunk)

        await io_test(aiofile_copy, src_file)


if __name__ == '__main__':
    asyncio.run(run_copy_test())
