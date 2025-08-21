#!/usr/bin/perl -w
##!/cygdrive/w/Applications/Perl64/bin/cygwin_perl 

use strict;
my $i;


my $f_in = $ARGV[0];

# open file
open (INF, "<", $f_in) or die "Cannot open $f_in for reading" ;

my %grp;
$grp{10000} = 0;
$grp{10001} = 1;
$grp{10002} = 2;
$grp{10003} = 0;
$grp{10004} = 0;
$grp{10005} = 0;
$grp{10006} = 0;
$grp{10007} = 0;
$grp{10008} = 0;
$grp{10009} = 0;
$grp{10500} = 0;
$grp{10501} = 1;
$grp{10502} = 2;
$grp{10503} = 0;
$grp{10504} = 0;
$grp{10505} = 0;
$grp{10506} = 0;
$grp{10507} = 0;
$grp{10508} = 0;
$grp{10159} = 3;
$grp{10160} = 3;

my $rem_col = 4;
my $date_col = 2;
my $sig_col = 1;
my $val_col = 3;
my $id_col = 0;

while (<INF>) {

	chomp;
	my @f = split /\,/,$_;
	
	my $bad = 1;
	
#	print "$_\n";
	
	$bad  = 0 if ($f[$rem_col] =~ /^NEGATIVE/);
	$bad  = 0 if ($f[$rem_col] =~ /^POSITIVE/ && $grp{$f[1]} == 1);
	$bad  = 0 if ($f[$rem_col] =~ /^NORMAL/);
	$bad  = 0 if ($f[$rem_col] =~ /^        /);
	$bad  = 0 if ($f[$rem_col] =~ /^[0-9]/ && $grp{$f[1]} == 3);
	
	next if ($bad == 1);
	
	my @d = split /-| /,$f[$date_col];
#	print "DATE $f[$date_col] $d[0] $d[1] $d[2]\n";
	my $date = $d[0].$d[1].$d[2];
	
	if ($grp{$f[$sig_col]} == 0) {
		print "$f[$id_col] $f[$sig_col] $date $f[$val_col]\n";
	}
	
	if ($grp{$f[$sig_col]} == 1) {
		my $val = -1;
		$val = 0 if ($f[$rem_col] =~ /^NEGATIVE/);
		$val = 1 if ($f[$rem_col] =~ /^POSITIVE/);
		if ($val >= 0) {
			print "$f[$id_col] $f[$sig_col] $date $val\n";
		}
	}
	
	if ($grp{$f[$sig_col]} == 2) {
		if ($f[$val_col] > 3 && $f[$val_col] < 13) {
			print "$f[$id_col] $f[$sig_col] $date $f[$val_col]\n";
		}
	}
	
	if ($grp{$f[$sig_col]} == 3) {
		my $val = -1;
		$val = $f[3] if ($f[$rem_col] =~ /^        /);
		if ($f[$rem_col] =~ /^[0-9]/) {
			print "!!!!!! weird line\n";
			my @b = split /-| /,$f[$rem_col];
			my $lb = @b;
			if ($lb == 2) {
				$val = ($b[0]+$b[1])/2;
			}
		}
		if ($val > 0) {
			print "$f[$id_col] $f[$sig_col] $date $val\n";
		}
	}
	
	
}
























