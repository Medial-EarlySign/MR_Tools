#!/cygdrive/w/Applications/Perl64/bin/cygwin_perl

use strict(vars) ;

# Params
die "Usage : $0 thin_signals_to_united.txt\n" unless (@ARGV==1) ;
my ($listOfFiles) = @ARGV ;

# Read mapping between ahdcodes and Medial codes (Macabbi based standard signal names)
open (IN,$listOfFiles) or die "Cannot open $listOfFiles" ;
my %files ;
my $total_nin = 0 ;
my $nin = 0 ;
while (<IN>) {
	next if (/InFile/) ;

	chomp ;
	my ($in,$out) = split /\t/,$_ ;
	$total_nin ++ ;
	$out =~ s/\//_over_/g ;
	$out =~s/\r//;
	if ($out ne "TBD" and $out ne "NULL") {
		push @{$files{$out}},$in ;
		$nin ++ ;
	}
}
close IN ;

my $nout = scalar keys %files ;
print STDERR "About to unite $nin files (out of $total_nin) into $nout files\n" ;

my $found = 0 ;

foreach my $out (keys %files) {
	print STDERR "Appending to United/$out ...\n" ;
	open (OUT,">United/$out") or die "Cannot open $out for writing" ;
	foreach my $in (@{$files{$out}}) {
		if (open (IN,"Common/$in")) {
			$found ++;
			while (<IN>) {
				chomp ;
				print OUT "$_\t$in\n" ;
			}
			close IN ;
		} else {
			print STDERR "Cannot find $in, skipping...\n"
		}
	}
	close OUT ;
}

print STDERR "Found $found files (out of $nin I looked for) and wrote them into $nout files\n" ;
