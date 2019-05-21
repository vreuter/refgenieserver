import os

from subprocess import run
from hashlib import md5
from warnings import warn

from const import *


def archive(rgc, args):
    """
    Takes the RefGenomeConfiguration object and builds the individual tar archives
    that can be then served with 'refgenies serve'. Additionally determines their md5 checksums, file sizes and
    updates the original refgenie config with these data

    :param RefGenomeConfiguration rgc: configuration object with the data to build the servable archives for
    :param argparse.Namespace args: arguments from the refgenies CLI
    """
    if args.force:
        print("build forced; file existence will be ignored")
    genomes = rgc.genomes_list()
    for genome in genomes:
        genome_dir = os.path.join(rgc[CFG_FOLDER_KEY], genome)
        target_dir = os.path.join(rgc[CFG_ARCHIVE_KEY], genome)
        genome_tarball = target_dir + TAR["ext"]
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        changed = False
        for asset_name in rgc.genomes[genome].keys():
            file_name = rgc.genomes[genome][asset_name][CFG_PATH_KEY]
            target_file = os.path.join(target_dir, asset_name + TGZ["ext"])
            if not os.path.exists(target_file) or args.force:
                changed = True
                input_file = os.path.join(genome_dir, file_name)
                print("creating asset '{}' from '{}'".format(target_file, input_file))
                _check_tar([input_file], target_file, TGZ["flags"])
                rgc.genomes[genome][asset_name][CFG_CHECKSUM_KEY] = _checksum(target_file)
                rgc.genomes[genome][asset_name][CFG_ARCHIVE_SIZE_KEY] = _size(target_file)
                rgc.genomes[genome][asset_name][CFG_ASSET_SIZE_KEY] = _size(input_file)
            else:
                print("'{}' exists. Nothing to be done".format(target_file))
        if changed or not os.path.exists(genome_tarball):
            print("creating genome tarball '{}' from: {}".format(genome_tarball, genome_dir))
            _check_tar([target_dir], genome_tarball, TAR["flags"])
    rgc_pth = rgc.write(args.config)
    print("builder finished; updated refgenie config file: '{}'".format(rgc_pth))


def _check_tar(path, output, flags):
    """
    Checks if file exists and tars it

    :param list[str] path: path to the file to be tarred
    :param str output: path to the result file
    :param str flags: tar command flags to use
    :return:
    """
    assert isinstance(flags, str), "flags are not string"
    assert isinstance(path, list), "path argument has to be a list"
    assert all(os.path.exists(x) for x in path), "one of the files ({}) does not exist".format(path)
    run("tar {} {} {}".format(flags, output, " ".join(path)), shell=True)


def _checksum(path):
    """
    Generates a md5 checksum for the file contents in the provided path

    :param str path: path to the file to generate checksum for
    :return str: checksum hash
    """
    try:
        cs = md5(open(path, 'rb').read()).hexdigest()
    except:
        warn("checksum could not be calculated for file: '{}'".format(path))
        cs = None
    return cs


def _size(path):
    """
    Gets the size the file or directory in the provided path

    :param str path: path to the file to check size of
    :return int: file size
    """
    if os.path.isfile(path):
        s = _size_str(os.path.getsize(path))
    elif os.path.isdir(path):
        s = 0
        symlinks = []
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    s += os.path.getsize(fp)
                else:
                    s += os.lstat(fp).st_size
                    symlinks.append(fp)
        if len(symlinks) > 0:
            warn("{} symlinks were found: '{}'".format(len(symlinks), "\n".join(symlinks)))
    else:
        warn("size could not be determined for: '{}'".format(path))
        s = None
    return _size_str(s)


def _size_str(size):
    """
    Converts the numeric bytes to the size string

    :param int|float size: file size to convert
    :return str: file size string
    """
    if isinstance(size, (int, float)):
        for unit in FILE_SIZE_UNITS:
            if size < 1024:
                return "{}{}".format(round(size, 1), unit)
            size /= 1024
    return size