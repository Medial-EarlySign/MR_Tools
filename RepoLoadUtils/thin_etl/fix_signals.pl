#!/cygdrive/w/Applications/Perl64/bin/cygwin_perl

use strict(vars) ;

# PARAMETERS
my $MAX_SIG = 5 ;
my $MAX_PCT_TO_IGNORE = 0.015 ;
my $MAX_SKEWED_DIST = 50 ;
my %formats = (1 => "%.0f" , 0.1 => "%.1f" , 0.01 => "%.2f") ;

# Params
die "Usage : $0 InstFile UnitFile CodeDepFile InDir OutDir" unless (@ARGV==5) ;
my ($instFile,$unitsFile,$codeDepFile,$inDir,$outDir) = @ARGV ;
die "$inDir cannot be the same as $outDir" if ($inDir eq $outDir) ;

# Read auxilary files
my $translator = read_unit_translations($unitsFile) ;
my $codeDep = read_code_dependecies($codeDepFile) ;

# Read instructions
my $instructions = read_instructions($instFile) ;

map {handle_signal($_,$instructions->{$_},$translator->{$_},$codeDep->{$_}, $inDir,$outDir)} sort keys %$instructions ;


# FUNCTIONS
sub read_code_dependecies {
	my ($codeDepFile) = @_ ;
	
	open (IN,$codeDepFile) or die "Cannot open $codeDepFile for reading" ;
	
	my $codeDep ;
	while (<IN>) {
		chomp;
		my ($signal,$inUnit,$codes,$outUnit) = split /\t/ ;
		$codeDep->{$signal}->{$inUnit}->{$codes} = $outUnit ;
	}
	close IN ;
	
	return $codeDep ;
}
	
sub read_unit_translations {
	my ($unitsFile) = @_ ;
	
	open (IN,$unitsFile) or die "Cannot open $unitsFile for reading" ;
	
	my $translator ;
	while (<IN>) {
		chomp ; 
		my ($signal,$unit,$factor) = split /\t/,$_  ;
		$translator->{$signal}->{$unit} = $factor ;
	}
	close IN ;
	
	return $translator ;
}

sub read_instructions {
	my ($instFile) = @_ ;
	
	open (IN,$instFile) or die "Cannot open $instFile for reading" ;
	
	my @header  ;
	my $instructions ;
	while (<IN>) {
		chomp ;
		my @line = split /\t/,$_ ;
		
		if (@header) {
			map {$instructions->{$line[0]}->{$header[$_]} = $line[$_ + 1] if ($line[$_ + 1] =~ /\S/)} (0..$#header) ;
		} else {
			@header = map {$line[$_]} (1..$#line) ;
		}
	}
	
	close IN ;
	
	foreach my $signal (keys %$instructions) {
		if (exists $instructions->{$signal}->{Ignore}) {
			my @ignores = split ",",$instructions->{$signal}->{Ignore} ;
			delete $instructions->{$signal}->{Ignore} ;
			map {$instructions->{$signal}->{Ignore}->{$_} = 1} @ignores ;
		}
		
		if (exists $instructions->{$signal}->{Factors}) {		
			print STDERR "SIGNAL: $signal FACTORS: $instructions->{$signal}->{Factors}\n";
			my @factors = split ",",$instructions->{$signal}->{Factors} ;
			delete $instructions->{$signal}->{Factors} ;
			@{$instructions->{$signal}->{Factors}} = @factors ;			
		}
		
		die "Cannot find format for resoultion ".$instructions->{$signal}->{Resolution}." for $signal" if (! exists $formats{$instructions->{$signal}->{Resolution}}) ;
	}
	
	return $instructions ;
}

sub handle_signal {
	my ($name,$instructions,$translator,$codeDep,$inDir,$outDir) = @_ ;
	print STDERR "Working on $name\n" ;
	map {print STDERR "$_ : $instructions->{$_}\n"} keys %$instructions ;
	my $baseUnit= $instructions->{Unit} ;
	map {print STDERR "Translator : $_ $baseUnit $translator->{$_}\n"} keys %$translator ;

	# Read
	open (IN,"$inDir/$name") or die "Cannot open $inDir/$name for reading " ;
	my %data ;
	my %info ;
	my %ignoreCount ;
	my %counters ;
	
	while (<IN>) {
		chomp ;
		my ($id,$date,$value,$unit,$codes) = split /\t/,$_ ;
		$unit = "IU/L" if ($unit eq "U/L") ; # Units IU/L == U/L
		
		if (exists $codeDep->{$unit}) {
			die "Cannot find code-dependent unit for $unit/$codes" if (! exists $codeDep->{$unit}->{$codes}) ;
			$unit = $codeDep->{$unit}->{$codes} ;
		}

		my $type = ($value == 0) ? 0 : 1 ;
		my $unit_type = ($unit eq "null value")  ? "null" : "nonnull" ;
		$counters{$unit_type}->{$type} ++ ;
		
		if ($unit eq "null value" or exists $instructions->{Ignore}->{$unit}) {
			$ignoreCount{$unit} ++ ;
		} else {
			push @{$data{$unit}},$value  ;
			push @{$info{$unit}},[$id,$date] ;
		}
	}
	close IN ;
	
	# Stats on null-value
	if (exists $counters{null}) {
		my %p_zero = map {($_ => $counters{$_}->{0}/($counters{$_}->{1} + $counters{$_}->{0}))} keys %counters ;
		print STDERR "$name : Null-Values ; N(0) = $counters{null}->{0} ; P(0) = $p_zero{null}\n" ;
		print STDERR "$name : Non-Null-Values ; N(0) = $counters{nonnull}->{0} ; P(0) = $p_zero{nonnull}\n" ;
	}
	
	# Handle most common unit
	my $maxCount = scalar @{$data{$baseUnit}} ;
	
	my $totalCount = 0 ;
	foreach my $unit (keys %data) {
		my $count = scalar @{$data{$unit}} ;
		if ($count > $maxCount) {
			print STDERR "WARNING: skipping $name : Unit $unit has [$count] values > [$maxCount] for base-unit $baseUnit\n"  ;
			return;
		}
		$totalCount += $count ;
	}
	print STDERR "$name : Read $totalCount reads\n" ;
	if ($totalCount == 0) {
		print STDERR "WARNING: skipping $name as it has no values\n"  ;
		return;
	}
	
	if ($instructions->{Factors}){
		print STDERR "Factors: @{$instructions->{Factors}}\n";
	}
	
	$data{$baseUnit} = internal_fix_factors($name,$baseUnit,$data{$baseUnit},$instructions->{Factors}) if ($instructions->{Factors}) ;
	
	my $moments = get_moments($data{$baseUnit}) ;
	map {print STDERR "$name : Base unit $baseUnit -- $_ :: $moments->{$_}\n"} keys %$moments ; 
	
	# Handle other units
	foreach my $unit (sort keys %data) {
		print STDERR "handling: $unit\n";
		next if ($unit eq $baseUnit) ;
		if (! exists $translator->{$unit}) {
			my $s = scalar(@{$data{$unit}});
			my $pct_of_max = $s/$maxCount;
			if ($pct_of_max <= $MAX_PCT_TO_IGNORE) {
				warn "WARNING : $name : Cannot translate [$unit] to [$baseUnit], but its ok as it has only $s values which are [$pct_of_max] from [$baseUnit]" ;
				next ;
			} else {
				die "$name : Cannot tranlsate [$unit] to [$baseUnit], aborting as it has $s values which are $pct_of_max from $baseUnit" ;
			}
		}
		translate($data{$unit},$translator->{$unit} ) ;
		fix_factors($name,$unit,$data{$unit},$instructions->{Factors},$moments) if ($instructions->{Factors}) ;
		
		print STDERR "completed translating and fixing: $unit\n";
		my $unit_moments = get_moments($data{$unit}) ;
		map {print STDERR "$name : $unit -- $_ :: $unit_moments->{$_}\n"} keys %$unit_moments ; 
	}
	
	map {print STDERR "$name : Ignored $ignoreCount{$_} measurements of unit $_\n"} keys %ignoreCount ;
	
	# Sort and write
	my @out_data ;
	foreach my $unit (sort keys %data) {
		for my $i (0..scalar(@{$data{$unit}})-1) {
			push @out_data,[$info{$unit}->[$i]->[0],$info{$unit}->[$i]->[1],sprintf($formats{$instructions->{Resolution}},$data{$unit}->[$i])] ;
		}
	}
	
	$instructions->{FinalFactor} = 1.0 if (! exists $instructions->{FinalFactor}) ;
	open (OUT,">$outDir/$name") or die "Cannot open $outDir/$name for writing " ;
	foreach my $rec (sort {$a->[0] <=> $b->[0] or $a->[1] <=> $b->[1]} @out_data) {
		printf OUT "%d\t$name\t%d\t%f\n",$rec->[0],$rec->[1],$rec->[2]*$instructions->{FinalFactor}  ;
	}
	return ;
}

sub translate {
	my ($data,$translator) = @_ ;
		
	if ($translator =~ /Formula/) {
		if ($translator eq "Formula1") {
			map {$data->[$_] = 100/$data->[$_]} (0..(scalar(@{$data})-1)) ;
		} elsif ($translator eq "Formula2") {
			map {$data->[$_] = 0.09148 * $data->[$_] + 2.152} (0..(scalar(@{$data})-1)) ;
		} else {
			die "Unknown translation formula \'$translator\'\n" ;
		}
	} else {
		map {$data->[$_] *= $translator} (0..(scalar(@{$data})-1)) ;
	}
}

sub get_mean_and_sdv {
	my ($data) = @_ ;
	
	my $n = scalar @$data ;
	my ($s,$s2) ;
	foreach my $val (@$data) {
		$s += $val ;
		$s2 += $val*$val ;
	}
	
	my $mean = $s/$n ;
	my $sdv = 0;
	if ($n > 1){
		$sdv = sqrt(($s2 - $s*$mean)/($n-1)) ;
	}
	return ($mean,$sdv) ;
}
	
	

sub get_moments { 
	my ($orig_data) = @_ ;
	
	my @data = sort {$a<=>$b} @$orig_data ;
	
	my $noisy = 1 ;
	while ($noisy) {
		my ($mean,$sdv) = get_mean_and_sdv(\@data) ;
		my @new_data = grep {$_ >= $mean - $MAX_SIG*$sdv and $_ <= $mean + $MAX_SIG*$sdv} @data ;
		
		if (scalar(@new_data) < scalar(@data)) {
			@data = @new_data ;
		} else {
			$noisy = 0 ;
		}
	}
	
	my ($mean,$sdv) = get_mean_and_sdv(\@data) ;
	my $n = scalar (@data) ;
	my $ntot = scalar @$orig_data ;
	my $nabove = scalar (grep {$_ > $mean + $MAX_SIG*$sdv} @$orig_data) ;
	my $nbelow = scalar (grep {$_ < $mean - $MAX_SIG*$sdv} @$orig_data) ;
	
	my $skew = 0.0;
	
	if ($sdv > 0.0){
		foreach my $val (@data) {
			my $v = ($val - $mean)/$sdv ;
			$skew += $v*$v*$v ;
		}
	}
	my $moments = {ntot => $ntot, n => $n, pbelow => ($nbelow+0)/$ntot, pabove => ($nabove+0)/$ntot, mean => $mean, sdv => $sdv, skew => $skew/$n} ;

}

# in each iteration we compute moments, we try multiplying each data by each factor and check if it makes it closer to the mean
sub internal_fix_factors {
	my ($name,$unit,$data,$factors) = @_ ;
		
	my @data = @$data ;
	my $change = 1 ;
	my %tot_change ;
	while ($change) {
		$change = 0 ;

		my $moments = get_moments(\@data) ;
		my ($abs_skew,$sgn_skew) = (abs($moments->{skew}),($moments->{skew} > 0 ? 1 : -1)) ;
		my $sk = $sgn_skew * exp(log($abs_skew)/3) ;
	
		my @new_data ;
		for my $value (@data) {
			my $z = ($value - $moments->{mean})/$moments->{sdv} ;
			my $d = $z*$z - $sk * $z ;
#			print STDERR "$value -> ($moments->{mean},$moments->{sdv}) -> $z ; ($sk) -> $d\n" ;
			my $optimal = 1.0 ;
			foreach my $factor (@$factors) {
				my $z = ($value*$factor - $moments->{mean})/$moments->{sdv} ;
				my $newD = $z*$z - $sk*$z ;
#				print STDERR "$value ... $factor ($moments->{mean},$moments->{sdv}) -> $z ; ($sk) -> $newD\n" ;
				if ($newD <= $MAX_SKEWED_DIST and $newD < $d) {
					print STDERR "$value :: at factor: [$factor] has better distance ($newD < $d) !\n" ;
					$optimal = $factor ;
					$d = $newD ;
				}
			}
			
			if ($optimal != 1.0) {
				$change ++ ;
				$tot_change{$optimal} ++ ;
			}
			push @new_data,$optimal*$value ;
		}
		
		@data = @new_data ;
		print STDERR "Changed $change values ...\n" ;
	}
	
	map {print STDERR "$name/$unit : Changed $tot_change{$_} values x$_\n"} keys %tot_change ;
	return \@data ;
}

# we use the moments we computed in the base unit, and try multiplying each data by each factor and check if it makes it closer to the mean
sub fix_factors {
	my ($name,$unit,$data,$factors,$moments) = @_ ;
		
	my @data = @$data ;
	
	my %tot_change ;
	
	my ($abs_skew,$sgn_skew) = (abs($moments->{skew}),($moments->{skew} > 0 ? 1 : -1)) ;
	my $sk = $sgn_skew * exp(log($abs_skew)/3) ;
	
	my @new_data ;
	for my $value (@data) {
		my $z = ($value - $moments->{mean})/$moments->{sdv} ;
		my $d = $z*$z - $sk * $z ;
#		print STDERR "$name -- $unit :: $value -> ($moments->{mean},$moments->{sdv}) -> $z ; ($sk) -> $d\n" ;
		my $optimal = 1.0 ;
		foreach my $factor (@$factors) {
			my $z = ($value*$factor - $moments->{mean})/$moments->{sdv} ;
			my $newD = $z*$z - $sk*$z ;
#			print STDERR "$name -- $unit :: $value ... $factor ($moments->{mean},$moments->{sdv}) -> $z ; ($sk) -> $newD\n" ;
			if ($newD <= $MAX_SKEWED_DIST and $newD < $d) {
				print STDERR "$value :: at factor: [$factor] has better distance ($newD < $d) !\n" ;
				$optimal = $factor ;
				$d = $newD ;
			}
		}
		
		$tot_change{$optimal} ++ if ($optimal != 1.0) ;
		push @new_data,$optimal*$value ;
	}
	
	@$data = @new_data ;
	
	map {print STDERR "$name/$unit : Changed $tot_change{$_} values x$_\n"} keys %tot_change ;
	return \@data ;
}			
	