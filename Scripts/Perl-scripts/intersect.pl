#!/usr/bin/env perl 

use strict(vars) ;


my ($file1,$file2) ;
my (@cols1,@cols2) ;
my ($rev,$tab) ;

if ($ARGV[0] eq "--help") {
	print STDERR "intersect.pl file-name-1 [columns-1] file-name-2 [columns-2] [-r/R] [-t/T]\n" ;
	print STDERR "Finds line in file-name-1 which have lines in file-name-2 where the values at columns-1 in file-name-1 are equal to the values at columns-2 in file-name-2\n" ;
	print STDERR "Lines are printed from file-name-1 at the order of their appearance there, unless -r/R , in which they appear at the order in file-name-2\n" ;
	print STDERR "Columns are defined by white-spaces, unless -t\T, in which case the delimeter is a SINGLE TAB\n" ;
	print STDERR "One of the file names may be \"-\" meaning STDIN\n" ;
	exit(0) ;
}

while (@ARGV[-1] =~ /^\-\S/) {
	my $flag = pop @ARGV ;
	$tab = 1 if ($flag eq "-t" or $flag eq "-T") ;
	$rev = 1 if ($flag eq "-r" or $flag eq "-R") ;
}

my $nvars = scalar @ARGV ;
die "Usage : intersect.pl file-name [columns] file-name [columns] [-r/R] [-t/T])" if ($nvars%2) ;

if ($nvars == 2) {
	($file1,$file2) = @ARGV ;
	@cols1 = (0) ;
	@cols2 = (0) ;
} else { 
	$file1 = shift @ARGV ;
	@cols1 = splice(@ARGV,0,($nvars-2)/2) ;
	$file2 = shift @ARGV ;
	@cols2 = @ARGV ;
}

die "Cannot handle intersection of two STDINS !" if ($file1 eq "-" and $file2 eq "-") ;

# Read file2
my $fh ;
if ($file2 eq "-") {
	$fh = \*STDIN ;
} else {
	open (IN,$file2) or die "Cannot open $file2 for reading" ;
	$fh = IN ;
}

my %positions ;
my @data ;

my $line = 0 ;
while (<$fh>) {
	$line++ ;
	
	chomp ;
	if ($tab) {
		@data = split /\t/,$_ ;
	} else {
		@data = split /\s+/,$_ ;
		shift @data if ($data[0] eq "") ;
	}
	
	my $index = join " ",map {$data[$_]} @cols2 ;
	$positions{$index} = $line if (! defined $positions{$index}) ;
}

close IN if ($file2 ne "-") ;

# Read file1
if ($file1 eq "-") {
	$fh = \*STDIN ;
} else {
	open (IN,$file1) or die "Cannot open $file1 for reading" ;
	$fh = IN ;
}

my @outlines ;
while (my $line = <$fh>) {
	chomp $line;
	if ($tab) {
		@data = split /\t/,$line ;
	} else {
		@data = split /\s+/,$line ;
		shift @data if ($data[0] eq "") ;
	}

	my $index = join " ",map {$data[$_]} @cols1 ;
	if (exists $positions{$index}) {
		if ($rev) {
			push @outlines,{line => $line, pos => $positions{$index}} ;
		} else {
			print "$line\n" ;
		}
	}
}

close IN if ($file1 ne "-") ;
	
map {print $_->{line}."\n"} sort {$a->{pos} <=> $b->{pos}} @outlines if ($rev) ;
	
