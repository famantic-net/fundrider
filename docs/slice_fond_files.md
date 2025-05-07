# Synopsis

slice\_fond\_files.pl \[-cflmntu\] \[-h\] \[-d &lt;result directory>\] \[-i &lt;number of funds per table>\] \[-w &lt;working directory>\]

# Description

This hack reads the downloaded fund files and slices the data so that each fund
is listed with its historical values. Some options only work in combinations.

Funds are bundled since they frequently change names. The bundling is
defined in the file `fond_names.yaml` which must reside in the same
directory as `slice_fond_files.pl` itself.

# Options

- -c

    Checks the fund hash for duplicate definitions, i.e. if a main fund name
    is also listed as part of some other bundle.

- -d

    with an argument can be given in which case the funds are printed
    to the subdirectory specified by the argument with the file name being the fund.

- -f

    Full listing, i.e. don't use the internal fund name hash to bundle funds.

- -i

    Sets the number of columns for each printed table. This option will only
    print to files. Files will be named fund\_tables\_#.\[html|csv\]. Where # is
    a sequence number that goes up to the total number of printed tables.
    Extension html or csv depend on whether -m or -t was invoked.

- -l

    Only lists the funds.

- -m

    Prints a html table (matrix) to STDOUT or files if -i is set.

    This works well for pasting directly into Excel (at least old Excel from around
    Y2K) as it automatically senses the table format.

- -n

    Prints a normalized logarithmic html or csv table. Can only be used with -m or -t.

- -p

    Purges the fund list of discontinued funds.

- -r

    Renew fund list. Will use the cached information and try to determine new names
    for discontinued funds based on the list of missing ones. The new list is saved
    as c&lt;fund\_names.new.yaml>.

- -s

    Lists stopped funds, i.e. funds no longer available either because of name
    change or because of being terminated.

- -t

    Prints a CSV table to STDOUT or files if -i set.

    This can be pasted into Libreoffice calc as unformatted text and imported with
    semicolons as delimiters.

- -u

    Lists unregistered funds, i.e. funds not in the internal fund hash and
    therefore not visible in the result printout, and exits.

- -w

    Specifies a working directory where the fund files are loctated. Result directory
    (if specified with -d option ) is created below this directory.

    If not invoked the current directory is used as working dir.

# Examples

- To create a normalized table of all value changes suitable for MS Excel

    `./slice\_fond\_files.pl -nw. | gzip -c > fund\_data.normalized.gz`

- To update the cache before running a fund list renewal

    `./slice\_fond\_files.pl -us`

- To splice all fund data into separate files for each fund

    `./slice\_fond\_files.pl -w . -d results`
