#!/cygdrive/w/Applications/Perl64/bin/cygwin_perl

use strict(vars) ;

# Read
my (%values,%counts) ;
my %resolution ;

while (<>) {
	chomp ;
	my ($id,$eventdate,$value,$unit,$source) = split /\t/,$_ ;
	$unit = "IU/L" if ($unit eq "U/L") ; # Units IU/L == U/L
	$counts{"$unit//$source"} ++ ;
	push @{$values{$unit}->{$source}},$value ;
	
	$resolution{get_res($value)} ++ ;	
}

map {print STDERR "At res [$_] : $resolution{$_}\n"} sort {$a<=>$b} keys %resolution ;

#map {print STDERR "$_\t$counts{$_}\n"} keys %counts ;

foreach my $type (sort {$counts{$b}<=>$counts{$a}} keys %counts) {
	my ($unit,$source) = split "//",$type ;
	analyze($values{$unit}->{$source},$unit,$source) if ($counts{$type} > 200);	
}

##############################################
sub get_res {
	my ($value) = @_ ;
	
	my $res = 100000 ;
	$res /= 10 while (int ($value/$res) != $value/$res) ;
	return $res
	#print STDERR "$value -> $res\n" ;
}
	
sub analyze {
	my ($values,$unit,$source) = @_ ;
	
	my @values = sort {$a<=>$b} @$values ;
	my $nvalues = scalar @values ;
	
	my $median = $values[int(($nvalues-1)/2)] ;
	print STDERR "[$unit]\t$source\t$nvalues\t$median\n" ;
	
	my %hist ;
	map {$hist{$_}++} @values ;
	my @keys = sort {$a<=>$b} keys %hist ;
	
	my $grp_size = 10 ;
	my %grp_max ;
	for my $i (0..$#keys-$grp_size+1) {
		my $max = 0 ;
		map {$max = $hist{$keys[$_]} if ($hist{$keys[$_]} > $max)} ($i..$i+$grp_size-1) ;
		$grp_max{$i} = $max ;
	}
	
	for my $i ($grp_size..$#keys-$grp_size) {
		if ($hist{$keys[$i]} > $grp_max{$i-$grp_size} and $hist{$keys[$i]} > $grp_max{$i+1}) {
			print STDERR " -- Found local max at $keys[$i] ($hist{$keys[$i]})\n" ;
		}
	}
}
	
	
