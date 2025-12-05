#!/usr/bin/env perl 

use strict(vars) ;

die "Usage : transpose.pl in/- [-t or -c]]\n" unless (@ARGV==1 or (@ARGV==2 and ($ARGV[1] eq "-t" or $ARGV[1] eq "-c"))) ;

my $in = shift @ARGV ;

my $fh ;
if ($in eq "-") {
	$fh = \*STDIN ;
} else {
	open (IN,$in) or die "Cannot open $in for reading" ;
	$fh = IN ;
}
my $tab = " ";
if (@ARGV) {
	$tab = $ARGV[0] eq "-t" ? "\t" : "," ;
}

my @data ;
my @line ;
while (<$fh>) {
	chomp; 
	if ($tab ne " ") {
		@line = split $tab,,$_ ;
	} else {
		@line = split ;
	}
	map {push @{$data[$_]},$line[$_]} (0..$#line) ;
}
close $fh ;

foreach my $rec (@data) {
	my $line = join $tab,@$rec ;
	print "$line\n" ;
}
