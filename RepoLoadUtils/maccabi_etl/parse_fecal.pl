#!/usr/bin/perl -w
##!/cygdrive/w/Applications/Perl64/bin/cygwin_perl 


use strict;
my $i;

#my @unsorted = (5,7,2,9,3,4,0,8,9,9);
#my @indexes = 0..$#unsorted;
#my @sorted_indexes = sort {$unsorted[$a] <=> $unsorted[$b]} @indexes;
#for ($i=0; $i<$#unsorted; $i++) {
#	print "$i $sorted_indexes[$i] $unsorted[$sorted_indexes[$i]]\n";
#}

my $n_args = @ARGV;
my $f_in = $ARGV[0];
my @fn;

for ($i=1; $i<$n_args; $i++) {
	$fn[$i-1] = $ARGV[$i];
}

#my $res_n = $fn[$n_args-2];
my $res_n = $fn[2];



# open file
open (INF, "<", $f_in) or die "Cannot open $f_in for reading" ;

my @pid;
my @dates;
my @res;
my @sort_by;
my @index;
my $n_lines = 0;
my ($year, $month, $day);
# go over file line by line
while (<INF>) {

	chomp;
	my @f = split /,/,$_;
	my $n = @f;
	my $to_take = 0;
	my $val = 0;
	
	if (($_ =~ /\xd7\x99\xd7\x91\xd7\x95\xd7\x99\xd7\x97/) || index($f[$res_n],"POSITIVE") != -1 || index($f[$res_n],"Positive") != -1 || index($f[$res_n],"positive") != -1) {
		$val++;
#		print "!!!!! FOUND ONE POSITIVE $val\n";
	}
	if (($_ =~ /\xd7\x99\xd7\x9c\xd7\x99\xd7\x9c\xd7\xa9/)  || index($f[$res_n],"NEGATIVE") != -1 || index($f[$res_n],"Negative") != -1 || index($f[$res_n],"negative") != -1) {
		$val--;
#		print "!!!!! FOUND ONE NEGATIVE $val\n";
	}
	if ($val == 0) {
		print "###>>> $_\n";
	} else {
		
		$pid[$n_lines] = $f[$fn[0]];
		
		# converting date
		if ($f[$fn[1]] =~ /\//) {
			$f[$fn[1]] =~ s/\// /g;
			my @fd = split / /,$f[$fn[1]];
			$year = $fd[2];
			$month = $fd[1];
			$day = $fd[0];		}
		elsif ($f[$fn[1]] =~ /\-/) {
			$f[$fn[1]] =~ s/\-/ /g;
			my @fd = split / /,$f[$fn[1]];
			$year = $fd[0];
			$month = $fd[1];
			$day = $fd[2];
		}

		$dates[$n_lines] = $year*10000+$month*100+$day;
		$res[$n_lines] = int(($val+1)/2);
		$sort_by[$n_lines] = $pid[$n_lines]*1000000+365*($year-1900)+30*($month-1)+($day-1);
		$index[$n_lines] = $n_lines;
		
#		print "$f[$fn[0]] $f[$fn[1]] :: $n_lines pid $pid[$n_lines] date $dates[$n_lines] res $res[$n_lines] sort $sort_by[$n_lines] $index[$n_lines] :: ";
#		print int(($val+1)/2);
#		print "\n";
		$n_lines++;
		
	}
#	last if ($n_lines > 100);
}

my @sorted_indexes = sort {$sort_by[$a] <=> $sort_by[$b]} @index;	
my $prev_pid = 0;
my $prev_dt = 0;
my $prev_s = 0;
my $n_tests = 0;
my $n_pos = 0;
my $rval;
for ($i=0; $i<$n_lines; $i++) {

	my $j = $sorted_indexes[$i];
	my $dist = $sort_by[$j] - $prev_s;
	print "## $i $j pid $pid[$j] date $dates[$j] res $res[$j] sort $sort_by[$j]\n";	
	if ($dist > 7 && $prev_pid>0) {
		$rval = $n_pos*100+$n_tests;
		print "$prev_pid FECAL_TEST $prev_dt $rval\n";

		$n_pos = $res[$j];
		$n_tests = 1;
	} else {
		$n_pos += $res[$j];
		$n_tests++;
	}
	$prev_pid = $pid[$j];
	$prev_dt = $dates[$j];
	$prev_s = $sort_by[$j];	
	
}
$rval = $n_pos*100+$n_tests;
print "$prev_pid FECAL_TEST $prev_dt $rval\n";
























