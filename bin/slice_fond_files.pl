#!/usr/bin/env perl
##!/home/eranac/local/bin/perl

use Getopt::Std;
use Time::Local;
use File::Glob ':glob';
use YAML;
use String::Similarity;
use Term::ReadKey;
use Date::Calc qw(Delta_Days);

=pod

=head1 Synopsis

slice_fond_files.pl [-cflmntu] [-h] [-d <result directory>] [-i <number of funds per table>] [-w <working directory>]

=head1 Description

This hack reads the downloaded fund files and slices the data so that each fund
is listed with its historical values. Some options only work in combinations.

Funds are bundled since they frequently change names. The bundling is 
defined in the file F<fond_hash_slices.pm> which must reside in the same 
directory as F<slice_fond_files.pl> itself.

=over 4

=item -c

Checks the fund hash for duplicate definitions, i.e. if a main fund name 
is also listed as part of some other bundle.

=item -d 

with an argument can be given in which case the funds are printed 
to the subdirectory specified by the argument with the file name being the fund.

=item -f

Full listing, i.e. don't use the internal fund name hash to bundle funds.

=item -i

Sets the number of columns for each printed table. This option will only 
print to files. Files will be named fund_tables_#.[html|csv]. Where # is 
a sequence number that goes up to the total number of printed tables. 
Extension html or csv depend on whether -m or -t was invoked.

=item -l 

Only lists the funds.

=item -m 

Prints a html table (matrix) to STDOUT or files if -i is set.

=item -n

Prints a normalized logarithmic html table. Can only be used with -m or -t.

=item -p

Purges the fund list of discontinued funds.

=item -r

Renew fund list. Will use the cached information and try to determine new names
for discontinued funds based on the list of missing ones. The new list is saved
as c<fund_names.new.yaml>.

=item -s

Lists stopped funds, i.e. funds no longer available either because of name
change or because of being terminated.

=item -t

Prints a comma separated table to STDOUT or files if -i set.

=item -u

Lists unregistered funds, i.e. funds not in the internal fund hash and 
therefore not visible in the result printout, and exits.

=item -w

Specifies a working directory where the fund files are loctated. Result directory
(if specified with -d option ) is created below this directory.

If not invoked the current directory is used as working dir.

=back

=head1 Examples

=over 4

=item To create a normalized table of all value changes suitable for MS Excel

./slice_fond_files.pl -nw. | gzip -c > fund_data.normalized.gz

=item To update the cache before running a fund list renewal

./slice_fond_files.pl -us

=item To splice all fund data into separate files for each fund

./slice_fond_files.pl -w . -d results

=back


=cut

getopts("cd:fi:lmnprstuw:h", \%opts);
$check_duplication = true if $opts{c};
$result_dir = $opts{d} if defined $opts{d};
$list_funds = true if $opts{l};
$full_listing = true if $opts{f};
$list_missing_funds = true if $opts{u};
$list_discontinued_funds = true if $opts{s};
$matrix_print = true if $opts{m};
$table_print = true if $opts{t};
$normalized_print = true if $opts{n};
$n_output_tables = $opts{i} if defined $opts{i};
$working_dir = $opts{w} if defined $opts{w};
$renew_funds = true if $opts{r};
$remove_discontinued = true if $opts{p};

$miss_file = "missing.txt";
$disc_file = "discontinued.txt";
$last_dates_file = "lastdates.txt";
$min_samples = 20;

$now = timelocal localtime;
$three_months_ago = $now - 15724800/2;
$six_months_ago = $now - 15724800;
$one_year_ago = $now - 15724800*2;
$max_tolerate_missing_fund = 14;    # Days

if ($opts{h}) {
	print qx(pod2text $0);
	exit 0;
}

#do "fond_hash_slices.pm";
do { undef local $/;
    open my $file, "<fund_names.yaml" or die "Can\t open: $!\n ";
    my $yaml = <$file>;
    close $file;
    my @data = Load $yaml;
    %fund_names = %{${$data[0]}{fund_names}};
    @full_list = @{${$data[0]}{full_list}};
    @exist_nonfull_list = @{${$data[0]}{exist_nonfull_list}};
};

if ($normalized_print and not ($matrix_print or $table_print)) {
    die "Normalized output can only be done with -m  or -t options.\n";
}

if ($check_duplication) {
	# Check the hash for duplicates
	my $found_dup;
	for my $fundkey1 (sort {$a cmp $b} keys %fund_names) {
		for $fundelem (@{$fund_names{$fundkey1}}) {
			for my $fundkey2 (sort {$a cmp $b} keys %fund_names) {
				unless ($fundkey2 eq $fundkey1) {
					if ($fundelem eq $fundkey2) {
						$found_dup = true;
						warn qq(Fund hash key "$fundkey2" is also in the element array "$fundkey1".\n);
					}
				}
			}
		}
	}
	unless ($found_dup) {print STDERR "No dups found.\n"}
	exit 0;
}

if ($working_dir and -e $working_dir and -d $working_dir) {
	$wdir = $working_dir;	
}
else {
	$wdir = ".";
}

if ($renew_funds or $remove_discontinued) {
	my $misslist;
	my $disclist;
	my $last_dates;
	do {
		undef local $/;
		open my $file, "<$wdir/cache/$miss_file";
		$misslist = <$file>;
		close $file;
		open my $file, "<$wdir/cache/$disc_file";
		$disclist = <$file>;
		close $file;
		open my $file, "<$wdir/cache/$last_dates_file";
		$last_dates = <$file>;
		close $file;
	};
	# Get rid of of first line (contains found number of funds)
	$misslist =~ s/[^\n]+\n//m;
	$disclist =~ s/[^\n]+\n//m;
	#my @fundlist = sort split /=/, join('=', @full_list, @exist_nonfull_list);
	my @disclist = sort split /\n/, $disclist;
	$last_dates = Load $last_dates;
	my %last_date = %{$last_dates};
	
    if (renew_funds) {
        my @misslist = sort split /\n/, $misslist;
        my $misscount;
        for my $missing (@misslist) {
            $misscount++;
            my $sim_score = 0;
            my $disc2replace;
            for my $discontinued (@disclist) {
                my $compare = similarity($discontinued, $missing);
                # If the similarity score is 1 they are identical.
                # If they are identical the fund name has been both discontinued as well as is missing from the registered fund set.
                # This means that a newer name could be active and that the old name could be a temporary replacement for an even older name.
                if ($compare < 1 and $compare > $sim_score) {
                    $sim_score = $compare;
                    $disc2replace = $discontinued;
                }
            }
            print "\n($misscount/@{[ $#misslist+1 ]})\n\t$disc2replace\t>\n\t$missing\n";
            print "Is this reasonable? [y/N] ";
            while (not defined ($answer = ReadLine(0, STDIN))) {}
            chomp $answer;
            unless ($answer =~ m/^[Yy]/) {
                print "Skipping...\n"
            }
            else {
                push @{$discreplace{$disc2replace}}, $missing;
            }
        }
        for my $disc2replace (sort {$a cmp $b} keys %discreplace) {
            #print "$disc2replace\n\t";
            #my $new_names = join "\n\t", @{$discreplace{$disc2replace}};
            #print $new_names;
            #print "\n";
            my $latest_date = "0000-00-00";
            my $replace_name = "";
            for my $n_fname (@{$discreplace{$disc2replace}}) {
                if ($last_date{$n_fname} gt $latest_date) {
                    $latest_date = $last_date{$n_fname};
                    $replace_name = $n_fname;
                }
            }
            #print "New name for the collection: $replace_name\n\n"
            
            # Add the updated collection to the fund map and remove the old entry
            $fund_names{$replace_name} = \@{$discreplace{$disc2replace}};
            if (defined $fund_names{$disc2replace}) {
                push @{$fund_names{$replace_name}}, @{$fund_names{$disc2replace}};
                delete $fund_names{$disc2replace};
            }
            else {
                push @{$fund_names{$replace_name}}, $disc2replace;
            }
            ## Remove duplicates from %fund_names
            #for my $key (keys %fund_names) {
            #    my %uniq, @uniq;
            #    for my $elem (@{$fund_names{$key}}) {
            #        $uniq{$elem} = $elem;
            #    }
            #    for my $elem (sort keys %uniq) {
            #        push @uniq, $elem;
            #    }
            #    $fund_names{$key} = \@uniq;
            #}
            
            # Update the display list
            my $i;
            for ($i=0; $i <= $#full_list; $i++) {
                if ($disc2replace eq $full_list[$i]) {
                    delete $full_list[$i];
                    push @full_list, $replace_name;
                }
            }
            for ($i=0; $i <= $#exist_nonfull_list; $i++) {
                if ($disc2replace eq $exist_nonfull_list[$i]) {
                    delete $exist_nonfull_list[$i];
                    push @exist_nonfull_list, $replace_name;
                }
            }
        }
    }
    if ($remove_discontinued) {
        for my $discfund (@disclist) {
            for ($i=0; $i <= $#full_list; $i++) {
                if ($discfund eq $full_list[$i]) {
                    delete $full_list[$i];
                }
            }
            for ($i=0; $i <= $#exist_nonfull_list; $i++) {
                if ($discfund eq $exist_nonfull_list[$i]) {
                    delete $exist_nonfull_list[$i];
                }
            }
        }
    }
	
    @full_list = sort grep {$_ ne ""} @full_list;
    @exist_nonfull_list = sort grep {$_ ne ""} @exist_nonfull_list;
    my %hash;
	$hash{fund_names} = \%fund_names;
	$hash{full_list} = \@full_list;
	$hash{exist_nonfull_list} = \@exist_nonfull_list;
	my $yaml = Dump \%hash;
	open my $fh, ">$wdir/fund_names.new.yaml" or die "Can't open '$wdir/fund_names.new.yaml': $!\n";
	print $fh $yaml;
	close $fh;
	
	exit 0;
}

@flist = glob("$wdir/fonder*");
$file_count = $#flist;

#for my $fund (keys %fund_names) {print $fund_names{$fund}[1]}
#exit 1;

if ($result_dir) {
	$dest_dir = $result_dir;
	if ($dest_dir eq "") {$dest_dir = "result_files"}
	unless (-e $dest_dir) {
		print "Creating $dest_dir\n";
		mkdir $dest_dir or die "Can't create $dest_dir\n$!\n";
	}
	print "Writing funds to $dest_dir\n";
}

$counter = 0;
@progrind = qw(- \ | /);
for my $file (sort {$a cmp $b} @flist) {
	$progress = sprintf "%d", $counter++/$file_count*100;
	$progrsign = $counter % 4;
	print STDERR "\rReading $file_count fund files $progrind[$progrsign] (${progress}%).";
	open FONDFILE, "<$file\n" or die "\nCan't open $file: $!\n";
	my @filec = <FONDFILE>;
	close FONDFILE;
	for my $filerow (@filec) {
		my @row = split /;/, $filerow;
		my $date = $row[0];
		if ($date eq "00-4-4") {$date = "2000-04-04"}
		my $fund_name = $row[1];
		my $value = $row[2];
		$fund_name =~ s:[,.]::g;
		$fund_name =~ s: +: :g;
		$fund_name =~ s:[/_]: :g;
		$fund_name = lc $fund_name;
		$value =~ s/,/./;
		
		unless ($full_listing) {
			# Catch duplicate names
			FUNDKEY: for my $fundkey (sort {$a cmp $b} keys %fund_names) {
						for $fundelem (@{$fund_names{$fundkey}}) {
							if ($fund_name eq $fundelem) {
								$fund_name = $fundkey;
								last FUNDKEY;
							}
						}
					}
		}
		
		$fund_hash{$fund_name} -> {$date} = $value;
		$last_date_with_value{$fund_name} = $date;
		# Count the number of samples for the specified fund name
		$fund_samples{$fund_name}++;
		$date_hash{$date} = "exists";
		my ($year, $month, $day);
		if (($year, $month, $day) = $date =~ m/(\d\d\d\d)-(\d\d)-(\d\d)/) {
			#print "::- $year, $month, $day\n";
			my $timestamp = timelocal "", "", "", $day, $month-1, $year;
			# If later than, i.e. if younger...
            #if ($timestamp > $one_year_ago) {
            #if ($timestamp > $six_months_ago) {
            if ($timestamp > $three_months_ago) {
				$current_funds{$fund_name} = "exists";
			}
		}
	}
}

# Corrections
unless ($full_listing) {
	for my $date (sort {$a cmp $b} keys %date_hash) {
		if ($date lt "1999-09-20") {$fund_hash{"seb avkastning"}{$date} = 0}
		if ($date gt "2000-05-08" and $date lt "2001-05-20") {$fund_hash{"seb läkemedelsfond"}{$date} = $fund_hash{"seb läkemedels- och bioteknikf"}{$date}}
		if ($date lt "2006-10-12") {undef $fund_hash{"merrill lynch global equity"}{$date}}
	}
}

print STDERR "\n";

{ # Save data in cache
	my $fh = "$wdir/cache/$last_dates_file";
	my $hash = \%last_date_with_value;
	my $yaml = Dump $hash;
	open my $fh, ">$wdir/cache/$last_dates_file" or die "Can't open '$last_dates_file': $!\n";
	print $fh $yaml;
	close $fh;
	@current_funds = sort keys %current_funds;
	push @registered_funds, @full_list;
	push @registered_funds, @exist_nonfull_list;
	@registered_funds = sort @registered_funds;
	$registered_funds = join "\n", @registered_funds;
	@missing_funds = map {$registered_funds !~ m/\Q$_\E/smg ? $_ : "" } @current_funds;
	@missing_funds = grep {$_ ne ""} @missing_funds;
	my @dates = sort {$a cmp $b} keys %date_hash;
	my @last_date = $dates[$#dates] =~ m/(\d\d\d\d)-(\d\d)-(\d\d)/;
	#for my $c_fund (sort {$a cmp $b} keys %fund_hash) {
	for my $c_fund (@current_funds) {
		#print "$c_fund\t$last_date_with_value{$c_fund}\n";
		@c_fund_ldate = $last_date_with_value{$c_fund} =~ m/(\d\d\d\d)-(\d\d)-(\d\d)/;
		if (Delta_Days(@c_fund_ldate, @last_date) > $max_tolerate_missing_fund) {
			push @discontinued_funds, $c_fund;
		}
	}
	open my $fh, ">$wdir/cache/$miss_file" or die "Can't open '$miss_file': $!\n";
	print $fh "@{[ $#missing_funds+1 ]} missing funds found.\n";
	for my $fund (@missing_funds) {print $fh "$fund\n";}
	close $fh;
	if ($list_missing_funds) {
		print STDOUT "@{[ $#missing_funds+1 ]} missing funds found.\n";
		for my $fund (@missing_funds) {print STDOUT "$fund\n";}
	}
	open my $fh, ">$wdir/cache/$disc_file" or die "Can't open '$disc_file': $!\n";
	print $fh "@{[ $#discontinued_funds+1 ]} discontinued funds found.\n";
	for my $fund (@discontinued_funds) {print $fh "$fund\n";}
	close $fh;
	if ($list_discontinued_funds) {
		print STDOUT "@{[ $#discontinued_funds+1 ]} discontinued funds found.\n";
		for my $fund (@discontinued_funds) {print STDOUT "$fund\n";}
	}
	exit 0 if ($list_missing_funds or $list_discontinued_funds);
}


unless ($matrix_print or $table_print) {
	for my $fund (sort {$a cmp $b} keys %fund_hash) {
		print "$fund\n";
		my $file_warned;
		for my $date (sort {$a cmp $b} keys %{$fund_hash{$fund}}) {
			unless ($result_dir) {
				unless ($list_funds) {
					print "\t$date,$fund_hash{$fund}{$date}\n";
				}
			}
			else {
				if (-e "$dest_dir/$fund" and not $file_warned) {
					warn "\t*** Warning: File exists! Data will be appended. ***\n";
					$file_warned = true;
				}
				if (open FUND, ">>$dest_dir/$fund") {
					$file_warned = true;
					print FUND "\t$date,$fund_hash{$fund}{$date}\n";
					close FUND;
				}
				else {warn "Can't open the file $dest_dir/$fund for writng: $!\n"}
			}
		}
	}
}
else {
	my $full_list = join "\n", @full_list;
	$full_list =~ s/([^\n]+)(:?\n|$)/<$1>/sg;
	my $exist_nonfull_list = join "\n", @exist_nonfull_list;
	$exist_nonfull_list =~ s/([^\n]+)(:?\n|$)/<$1>/sg;
	my $i = 0;
	for my $fund (sort {$a cmp $b} keys %fund_hash) {
		$fund_regex = "<$fund>";
		$fund_regex =~ s/ +/\\s+/g;
		$fund_regex =~ s/([().\$])/\\$1/g;
		if (defined $full_listing or $full_list =~ m/$fund_regex/sm or $exist_nonfull_list =~ m/$fund_regex/sm) {
			$fund_arr[$i++] = $fund;
		}
	}

	if ($matrix_print) {
		print << "EOSTART";
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2//EN">
<html>
<head>
<meta content="Fund info from slice_fond_files.pl" name="generator">
<title></title>
</head>
<body>

EOSTART
	}
	elsif ($table_print) {
		print "# Fund info from slice_fond_files.pl";
	}
	
	my $max_width = 256;	# So that the width doesn't exceed an Excel worksheet.
	my $found_tables = $#fund_arr+1;
	my $max_tables = $found_tables / $max_width;
	if (defined $n_output_tables) {$n_tables = $n_output_tables}
	else {$n_tables = $found_tables}
	my $n_table_rows = $found_tables / $n_tables;
	for (my $table=0; $table<($n_table_rows); $table++) {
		if ($matrix_print) {
			print "<table>\n";
			print "<tr>\n<td></td>";
		}
		elsif ($table_print) {
			print "\n# ,";
		}
		#for my $fund (sort {$a cmp $b} keys %fund_hash) 
		for (my $i=($n_tables*$table); $i<=(($n_tables*$table)+$n_tables); $i++) {
			if ($i > ($#fund_arr)) {last}
			print "<td>" if $matrix_print;
			for my $fund (@{$fund_names{$fund_arr[$i]}}) {
				print "[$fund]";
			}
			if ($matrix_print) {print "</td>";}
			elsif ($table_print) {print ",";}
		}
		if ($matrix_print) {print "\n</tr>\n<tr>\n<td></td>";}
		elsif ($table_print) {print "\n# ,";}
		for (my $i=($n_tables*$table); $i<=(($n_tables*$table)+$n_tables); $i++) {
			if ($i > ($#fund_arr)) {last}
			if ($matrix_print) {print "<td>$fund_arr[$i]</td>";}
			elsif ($table_print) {print "$fund_arr[$i],";}
		}
		#print "\n</tr>\n<tr>\n";
		for my $date (sort {$a cmp $b} keys %date_hash) {
			if ($matrix_print) {
				print "\n</tr>\n<tr>\n";
				print "<td>$date</td>";
			}
			elsif ($table_print) {
				print "\n$date,";
			}
			#for my $fund (sort {$a cmp $b} keys %fund_hash) 
			for (my $i=($n_tables*$table); $i<=(($n_tables*$table)+$n_tables); $i++) {
				if ($i > ($#fund_arr)) {last}
				unless ($normalized_print) {
					if (defined $fund_hash{$fund_arr[$i]}{$date}) {
						if ($matrix_print) {print "<td>$fund_hash{$fund_arr[$i]}{$date}</td>";}
						elsif ($table_print) {print "$fund_hash{$fund_arr[$i]}{$date},";};
					}
					else {
						if ($matrix_print) {print "<td>x</td>";}
						elsif ($table_print) {print "x,";};
					}
				}
				else {
					if (defined $fund_hash{$fund_arr[$i]}{$date} and $fund_hash{$fund_arr[$i]}{$date} > 0) {
						my $norm_value = sprintf "%.3f", log($fund_hash{$fund_arr[$i]}{$date} / $fund_hash{$fund_arr[$i]}{$last_date_with_value{$fund_arr[$i]}}) / log(10);
						if ($matrix_print) {print "<td>$norm_value</td>";}
						elsif ($table_print) {print "$norm_value,"};
					}
					else {
						if ($matrix_print) {print "<td></td>";}
						elsif ($table_print) {print ",";}
					}
				}
			}
			#print "</tr>\n<tr>\n";
		}
		if ($matrix_print) {
			print "\n</tr>";
			print "\n</table>\n";
		}
		elsif ($table_print) {
			print "\n";
		};
	}
	if ($#missing_funds > -1) {
		if ($matrix_print) {
			print qq(<p><font size="+2"><b>Note: @{[ $#missing_funds+1 ]} funds have been left out that exist in the processed files.</font> (List them with the -u option.)</b>\n</p>);
			#print "<p></p>\n";
		}
		elsif ($table_print) {
			print qq(# Note: @{[ $#missing_funds+1 ]} funds have been left out that exist in the processed files.</font> (List them with the -u option.));
		};
	}
	print "</body>" if $matrix_print;
}




