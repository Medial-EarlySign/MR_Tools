#!/usr/bin/env perl 

use strict(vars) ;


my ($file1,$file2) ;
my ($col1,$col2) ;
my @cols2 ;
my ($tab,$missing);

if (@ARGV[0] eq "--help") {
	print STDERR "paste.pl file-name-1 columns-1 file-name-2 columns-2 columns-from-2 [-t/T] [-m/M]\n" ;
	print STDERR "Finds, for each line in file-name-1 with given values at columns-1 the lines in file-name-2 with the same values at columns-2 and prints the columns-from-2 values\n" ;
	print STDERR "If columns-1 or columns-2 contain more than one column numnber, they should be comma separated.\n";
	print STDERR "Columns are defined by white-spaces, unless -t/T, in which case the delimeter is a SINGLE TAB\n" ;
	print STDERR "Column numbering is zero-origin.\n";
	print STDERR "If the -m/M flag is on, lines in file-name-1 without matching lines in file-name-2 are printed with \"-\"s replacing the values\n" ;
	print STDERR "One of the file names may be \"-\" meaning STDIN\n" ;
	exit(0) ;
}

while (@ARGV[-1] =~ /\-\S/) {
	my $flag = pop @ARGV ;
	$tab = 1 if ($flag eq "-t" or $flag eq "-T") ;
	$missing = 1 if ($flag eq "-m" or $flag eq "-M") ;
}

my $nvars = scalar @ARGV ;
die "Usage : paste.pl file-name-1 columns-1 file-name-2 columns-2 columns-from-2 [-t/T]" unless ($nvars > 4) ;
my ($file1,$col1,$file2,$col2,@addcols2) = @ARGV ;
my @cols1 = split(/,/, $col1);
my @cols2 = split(/,/, $col2);
my $sep = $tab?"\t":" " ;

die "Cannot handle intersection of two STDINS !" if ($file1 eq "-" and $file2 eq "-") ;

# Read file2
my $fh ;
if ($file2 eq "-") {
	$fh = \*STDIN ;
} else {
	open (IN,$file2) or die "Cannot open $file2 for reading" ;
	$fh = IN ;
}

my %data ;
my @data ;

while (<$fh>) {
	chomp ;
	if ($tab) {
		@data = split /\t/,$_ ;
	} else {
		@data = split /\s+/,$_ ;
		shift @data if ($data[0] eq "") ;
	}
	
	push @{$data{join($sep, @data[@cols2])}}, (join $sep, @data[@addcols2]) ;
}

my $complete = join $sep,("-")x(scalar @addcols2) ;

close IN if ($file2 ne "-") ;

# Read file1
if ($file1 eq "-") {
	$fh = \*STDIN ;
} else {
	open (IN,$file1) or die "Cannot open $file1 for reading" ;
	$fh = IN ;
}

while (my $line = <$fh>) {
	chomp $line;
	if ($tab) {
		@data = split /\t/,$line ;
	} else {
		@data = split /\s+/,$line ;
		shift @data if ($data[0] eq "") ;
	}

	if (exists $data{join($sep, @data[@cols1])}) {
		map {print "$line$sep$_\n"} @{$data{join($sep, @data[@cols1])}} 
	} elsif ($missing) {
		print "$line$sep$complete\n" ;
	}
}

close IN if ($file1 ne "-") ;
	
