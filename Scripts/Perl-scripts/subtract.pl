#!/usr/bin/env perl 

use strict(vars) ;


my ($file1,$file2) ;
my (@cols1,@cols2) ;
my ($rev,$tab) ;

if (@ARGV[0] eq "--help") {
	print STDERR "subtract.pl file-name-1 [columns-1] file-name-2 [columns-2] [-t/T]\n" ;
	print STDERR "Finds line in file-name-1 which donnot have lines in file-name-2 where the values at columns-1 in file-name-1 are equal to the values at columns-2 in file-name-2\n" ;
	print STDERR "Columns are defined by white-spaces, unless -t\T, in which case the delimeter is a SINGLE TAB\n" ;
	print STDERR "One of the file names may be \"-\" meaning STDIN\n" ;
	exit(0) ;
}

while (@ARGV[-1] =~ /\-\S/) {
	my $flag = pop @ARGV ;
	$rev = 1 if ($flag eq "-r" or $flag eq "-R") ;
}

my $nvars = scalar @ARGV ;
die "Usage : subtract.pl file-name [columns] file-name [columns] [-t/T]" if ($nvars%2) ;

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
	}

	my $index = join " ",map {$data[$_]} @cols1 ;
	print "$line\n" if (! exists $positions{$index}) ;
}

close IN if ($file1 ne "-") ;
	
