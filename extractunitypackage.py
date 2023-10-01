#!/usr/bin/env python
#
# UnityPackage Extractor
#
# Extracts files/folders from a .unitypackage file, reading the 'pathname'
# files it contains to rebuild a "readable" file/folder structure.

import os
import stat
import shutil
import sys
import tarfile
import argparse

import tkinter as tk
from tkinter import filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES


def parsePackage(
    srcPath: str, outputBaseDir: str = None, force: bool = False
) -> (bool, str):
    """Extract UnityPackage"""
    name, extension = os.path.splitext(srcPath)

    outputDir = ""
    if outputBaseDir is None:
        outputDir = os.path.join(os.path.dirname(srcPath), name)
    else:
        outputDir = os.path.join(outputBaseDir, name)
    workingDir = "./.working"

    # can't proceed if the output dir exists already
    # but if the temp working dir exists, we clean it out before extracting
    if os.path.exists(outputDir):
        if not force:
            return (False, f"Output dir {outputDir} exists. Aborting.")
        shutil.rmtree(outputDir)

    if os.path.exists(workingDir):
        shutil.rmtree(workingDir)

    # extract .unitypackage contents to a temporary space
    tar = tarfile.open(srcPath, "r:gz")
    tar.extractall(workingDir)
    tar.close()

    # build association between the unitypackage's root directory names
    # (which each have 1 asset in them) to the actual filename (stored in the 'pathname' file)
    mapping = {}
    for i in os.listdir(workingDir):
        rootFile = os.path.join(workingDir, i)
        asset = i

        if os.path.isdir(rootFile):
            realPath = ""

            # we need to check if an 'asset' file exists (sometimes it won't be there
            # such as when the 'pathname' file is just specifying a directory)
            hasAsset = False

            for j in os.listdir(rootFile):
                # grab the real path
                if j == "pathname":
                    lines = [line.strip() for line in open(os.path.join(rootFile, j))]
                    realPath = lines[0]  # should always be on the first line
                elif j == "asset":
                    hasAsset = True

            # if an 'asset' file exists in this directory, then this directory
            # contains a file that should be moved+renamed. otherwise we can
            # ignore this directory altogether...
            if hasAsset:
                mapping[asset] = realPath

    # mapping from unitypackage internal filenames to real filenames is now built
    # walk through them all and move the 'asset' files out and rename, building
    # the directory structure listed in the real filenames we found as we go

    os.makedirs(outputDir)

    for asset in mapping:
        path, filename = os.path.split(mapping[asset])

        destDir = os.path.join(outputDir, path)
        destFile = os.path.join(destDir, filename)
        source = os.path.join(workingDir, asset, "asset")

        if not os.path.exists(destDir):
            os.makedirs(destDir)

        shutil.move(source, destFile)

        # change file permissions for unix because under mac os x
        # (perhaps also other unix systems) all files are marked as executable
        # for safety reasons os x prevent the access to the extracted files
        os.chmod(destFile, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

        print(asset + " => " + mapping[asset])

    # done, cleanup any leftovers...
    shutil.rmtree(workingDir)

    return (True, outputDir)


class ExtractApp(TkinterDnD.Tk):
    def __init__(self, width: int = 640, height: int = 480):
        super().__init__()

        self.title("UnityPackage Extractor")
        self.geometry(f"{width}x{height}")
        self.minsize(width, height)

        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.extract)

        # configure
        confFrame = tk.Frame(self)
        confFrame.grid(row=3, column=1)
        confFrame.columnconfigure(0, weight=1)
        extractButton = tk.Button(confFrame, text="Extract", command=self.extract)
        extractButton.grid(row=0, column=0)

        # logs

    def extract(self, e):
        print(e.data)
        (successful, msg) = parsePackage(
            srcPath=e.data, outputBaseDir=None, force=False
        )
        if not successful:
            print(msg)
        else:
            print("")
            print(f"Done. Result saved in {msg}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UnityPackage Extractor")
    parser.add_argument(
        "-i",
        "--input_file",
        type=str,
        help=".unitypackage file. The part of the filename before the extension will be used as the name of the directory that the packages contents will be extracted to.",
    )
    parser.add_argument(
        "-f",
        "--force",
        default=False,
        action="store_true",
        help="If the file already exists, delete it and start over.",
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        type=str,
        help="optional path where the package's files will be extracted to. (If omitted, the current working directory is used)",
    )
    args = parser.parse_args()
    if args.input_file is not None:
        # CUI
        (successful, msg) = parsePackage(
            srcPath=args.input_file, outputBaseDir=args.output_dir, force=args.force
        )
        if not successful:
            print(msg)
            sys.exit(1)
        else:
            print("")
            print(f"Done. Result saved in {msg}.")
    else:
        # gui
        app = ExtractApp()
        app.mainloop()
