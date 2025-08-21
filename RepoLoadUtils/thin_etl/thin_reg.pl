#!/usr/local/bin/perl 

use strict;
use FileHandle;

sub hash_to_str {
    my ($h) = @_;

    my $res = "";
    map {$res .= $_ . " => " . $h->{$_} . "; ";} sort keys %$h;

    return $res;
}

sub open_file {
    my ($fn, $mode) = @_;
    my $fh;
    
#   print STDERR "Opening file $fn in mode $mode\n";
    $fn = "/dev/stdin" if ($fn eq "-");
    $fh = FileHandle->new($fn, $mode) or die "Cannot open $fn in mode $mode";

	print STDERR "Successfuly opened $fn in mode $mode\n" ;
	
    return $fh;
}

sub read_medcode_file {
    my ($fh) = @_;

    my $res = {};
    while (<$fh>) {
	chomp;
	my ($code, $nrec, $npat, $desc, $comment, $status, $type, $organ) = split(/\t/);
	$desc =~ s/ *$//;
	$res->{$code} = {desc => $desc, status => $status, type => $type, organ => $organ};
	print STDERR "CBC readcode $code:\t" . hash_to_str($res->{$code}) . "\n";
    }

    printf STDERR "Read %d CBC readcodes\n", scalar(keys %$res);
    return $res;
}

sub read_med_hist_codes_file {
    my ($fh) = @_;

    my $res = {};
    while (<$fh>) {
	chomp;
	my ($code, $info, $type, $intrnl_code) = split(/\t/);
	$res->{$code} = {code => $intrnl_code, desc => $type . "; " . $info};
	print STDERR "MEDHIST readcode $code:\t" . hash_to_str($res->{$code}) . "\n";
    }

    printf STDERR "Read %d MEDHIST readcodes\n", scalar(keys %$res);
    return $res;
}

sub check_date {
    my ($date) = @_; # 20070825

    my ($y, $m, $d) = 
	(substr($date, 0, 4),
	 substr($date, 4, 2),  
	 substr($date, 6, 2));
    
    return ($y >= 1900 && $m >= 1 && $m <= 12 && $d >= 1 && $d <= 31);
}

sub format_date {
    my ($date) = @_; # 20070825

    my $eDate = 
	substr($date, 4, 2) . "/" . 
	substr($date, 6, 2) . "/" .  
	substr($date, 0, 4);
    
    return $eDate; # 08/25/2007
}

sub date2num {
    my ($date) = @_; # 20070825

    my $res = 
	substr($date, 0, 4) * 372 + 
	substr($date, 4, 2) * 31 +  
	substr($date, 6, 2);
    
    return $res;
}

sub translate_medcode_to_icd9_primary_site_code {

	my $med2icd = {
		"B130.00"	=> "C18.3",
		"B803000"	=> "C18.3",
		"B131.00"	=> "C18.4",
		"B803100"	=> "C18.4",
		"B132.00"	=> "C18.6",
		"B133.00"	=> "C18.7",
		"B803300"	=> "C18.7",
		"B134.00"	=> "C18.0",
		"B134.11"	=> "C18.0",
		"B803400"	=> "C18.0",
		"B135.00"	=> "C18.1",
		"B803500"	=> "C18.1",
		"B136.00"	=> "C18.2",
		"B803600"	=> "C18.2",
		"B137.00"	=> "C18.5",
		"B803700"	=> "C18.5",
		"B575.00"	=> "C18.8",
		"B13..00" 	=> "C18.9",
		"B13z.11"	=> "C18.9",
		"B1z0.11"	=> "C18.9",
		"B13z.00"	=> "C18.9",
		"B902400"	=> "C18.9",
		"B13y.00"	=> "C18.9",
		"BB5N.00"	=> "C18.9",
		"B803z00"	=> "C18.9",
		"B803.00"	=> "C18.9",
		"B140.00"	=> "C19.9",
		"B804000"	=> "C19.9",
		"B141.00"	=> "C20.9",
		"B141.11"	=> "C20.9",
		"B141.12"	=> "C20.9",
		"B804100"	=> "C20.9",
		"B14..00"	=> "C21.8",
		"B14y.00"	=> "C21.8",
	};
	
	my ($medcode) = @_;
	my $icd = (exists $med2icd->{$medcode}) ? $med2icd->{$medcode} : 0;
	
	return $icd;
}

sub handle_single_pat {
    my ($pat_recs, $nr, 
	$codes, $reg_fh,
	$med_hist_codes, $med_hist_recs_fh) = @_;

    print STDERR "Working on patient $nr\n";
    my @pre_reg_recs;
    for (@$pat_recs) {
		# print STDERR $_ . "\n";
		my $medflag = substr($_, 40, 1);
		next if ($medflag ne "R" && $medflag ne "S");

		my $medcode = substr($_, 32, 7);
		my $date = substr($_, 11, 8);
	
		if (exists $med_hist_codes->{$medcode}) {
			my $mh = $med_hist_codes->{$medcode};
			$med_hist_recs_fh->print(join("\t", $nr, $mh->{code}, $date, $mh->{desc}) . "\n");
		}

		next unless (exists $codes->{$medcode}); 
		my $info = $codes->{$medcode};
	
		print STDERR join("\t", "MED:", $nr, $date, $medcode, $info->{desc},
						$info->{status}, $info->{type}, $info->{organ}) . "\n";

		push @pre_reg_recs, {
			date => $date, 
			desc => $info->{desc}, status => $info->{status}, 
			type => $info->{type}, organ => $info->{organ},
			medcode => $medcode,
		};
		print STDERR hash_to_str($pre_reg_recs[-1]) . "\n";
    }

    my $pre_reg_skip = {};
    my $back_date = {};
    # determine anciliary or morphology cancer records that should be associated with more specific cancer records
	# i = anc/morph, j = cancer event . (j - 2 months) < i
	# i would be skipped and j will get i's date if its earlier
    for (my $i = 0; $i < @pre_reg_recs; $i++) {
		next unless ($pre_reg_recs[$i]->{status} eq "anc" || $pre_reg_recs[$i]->{status} eq "morph");
		my $date_i = date2num($pre_reg_recs[$i]->{date});
		for (my $j = 0; $j < @pre_reg_recs; $j++) {
			next if ($j == $i);
			# print STDERR "$i: " . hash_to_str($pre_reg_recs[$i]) . " <=> " . "$j: " . hash_to_str($pre_reg_recs[$j]) . "\n";
			next unless ($pre_reg_recs[$j]->{status} eq "cancer");
			my $date_j = date2num($pre_reg_recs[$j]->{date});
			if (($date_i > $date_j) ||
				($date_i + 62 > $date_j)) {
				printf STDERR "$i: Cancer anciliary/morphology record $i is associated with record $j (%s = $date_i - %s = $date_j = %d days) and is skipped\n", $pre_reg_recs[$i]->{date}, 
					$pre_reg_recs[$j]->{date}, $date_i - $date_j;
				$pre_reg_skip->{$i} = 1;
				if ($date_i < $date_j) {
					$back_date->{$j} = $pre_reg_recs[$i]->{date};
					printf STDERR "$i: Cancer record $j backdated to %s \n", $back_date->{$j};
				}
				last;
			}   		
		}
    }

    for (my $i = 0; $i < @pre_reg_recs; $i++) {
		next if (exists $pre_reg_skip->{$i});
		my $prc = $pre_reg_recs[$i];
		# print STDERR $nr, ": ", hash_to_str($prc), "\n";
		my ($date, $status, $type, $organ, $medcode) = ($prc->{date}, 
												$prc->{status}, $prc->{type}, $prc->{organ}, $prc->{medcode});
		next if ($status eq "ignore" or $status eq "benign");
		$date = $back_date->{$i} if (exists $back_date->{$i});
		my $eDate = format_date($date);
		my $icd = translate_medcode_to_icd9_primary_site_code($medcode);

		# change certain cancer entries to the terms used in Maccabi's registry
		if ($status eq "cancer") {
			if ($type eq "crc") {
				$status = "Digestive Organs";
				$type = "Digestive Organs";;
				$organ = ($organ =~ m/rectum/i) ? "Rectum" : "Colon";
			}
			if ($type eq "oeso") {
				$status = "Digestive Organs";
				$type = "Digestive Organs";;
				$organ = "Esophagus";
			}
			if ($type eq "stom") {
				$status = "Digestive Organs";
				$type = "Digestive Organs";;
				$organ = "Stomach";
			}
			if ($type eq "liver") {
				$status = "Digestive Organs";
				$type = "Digestive Organs";;
				$organ = "Liver+intrahepatic bile";
			}
			if ($type eq "lung") {
				$status = "Respiratory system";
				$type = "Lung and Bronchus";
				$organ = "Unspecified";
			}
			if ($type eq "pancreas") {
				$status = "Digestive Organs";
				$type = "Digestive Organs";
				$organ = "Pancreas";
			}
			if ($type eq "bladder") {
				$status = "Urinary Organs";
				$type = "Urinary Organs";
				$organ = "Bladder";
			}
			if ($type eq "prostate") {
				$status = "Male genital organs";
				$type = "Prostate";
				$organ = "Prostate";
			}
			if ($type eq "ovary") {
				$status = "Female genital organs";
				$type = "Ovary";
				$organ = "Ovary";
			}
		}

		print STDERR "REG: $nr,0,0,0,0,$eDate,$medcode,$icd,0,0,0,0,0,0,$status,$type,$organ,0,0\n";	
		$reg_fh->print("$nr,0,0,0,0,$eDate,$medcode,$icd,0,0,0,0,0,0,$status,$type,$organ,0,0\n");
    }
}

# === main ===

# example arguments:
# --nr_offset 0 --pat_fn /cygdrive/x/THIN_w_New_Controls_Feb2013/old_aff_w_new_ctrl_pat.csv --rem_fn /cygdrive/c/Data/THIN/pat_half_code2nr --med_fn /cygdrive/x/THIN_w_New_Controls_Feb2013/old_aff_w_new_ctrl_med.csv --ahd_fn /cygdrive/x/THIN_w_New_Controls_Feb2013/old_aff_w_new_ctrl_ahd.csv --cbc_codes_fn /cygdrive/t/THIN_train_x/med_code_cbc_lookup.txt --cbc_dist_fn /cygdrive/c/Data/THIN/cbc_dist_params_after_edit.tsv --codes_fn //server/Work/CRC/FullOldTHIN/thin_cancer_medcodes_info_25Feb_2015_w_morph.txt --id2nr_fn /cygdrive/x/Test/THIN_w_New_Controls_Feb2013/old_aff_w_new_ctrl_id2nr --yob_fn /cygdrive/x/Test/THIN_w_New_Controls_Feb2013/old_aff_w_new_ctrl_yob --status_fn /cygdrive/x/Test/THIN_w_New_Controls_Feb2013/old_aff_w_new_ctrl_status --dmg_fn /cygdrive/x/Test/THIN_w_New_Controls_Feb2013/old_aff_w_new_ctrl_dmg --cbc_fn /cygdrive/x/Test/THIN_w_New_Controls_Feb2013/old_aff_w_new_ctrl_cbc --reg_fn /cygdrive/x/Test/THIN_w_New_Controls_Feb2013/old_aff_w_new_ctrl_reg


# follows is a bypass allowing to write _ instead of space for some names
$ARGV[3] =~ s/EPIC_65/EPIC 65/;
$ARGV[5] =~ s/EPIC_88/EPIC 88/;
$ARGV[7] =~ s/EPIC_65/EPIC 65/;

my $p = {
	id2nr_fn => "/server/Work/Users/Ido/THIN_ETL/ID2NR",
	med_fn => "/server/Data/THIN/EPIC\ 88/MedialResearch_med.csv_half",
	#med_fn => "/server/Work/Users/Ido/THIN_ETL/reg/temp_a681102kd.med_inp_for_perl",
	codes_fn => "/server/Work/CRC/FullOldTHIN/thin_cancer_medcodes_info_25Feb_2015_w_morph.txt",
	reg_fn => "/server/Work/Users/Ido/THIN_ETL/reg/perl_output",
};

# offset for internal numbering
my $nr_offset = 0;
$nr_offset = $p->{nr_offset} if (exists $p->{nr_offset});

# input files
my $med_fh = open_file($p->{med_fn}, "r");

my $codes_fh = open_file($p->{codes_fn}, "r");

my $med_hist_codes_fh = undef;
if (exists $p->{med_hist_codes_fn}) { # read medical history codes
    $med_hist_codes_fh = open_file($p->{med_hist_codes_fn}, "r");
}

# output files
my $reg_fh = open_file($p->{reg_fn}, "w");
my $med_hist_recs_fh = undef;
if (exists $p->{med_hist_codes_fn}) { 
    $med_hist_recs_fh = open_file($p->{med_hist_recs_fn}, "w");
}

# process file of cancer-related medcodes with relevant annotation
my $codes = read_medcode_file($codes_fh);

# process file of CRC-related medical history medcodes
my $med_hist_codes = {};
if (exists $p->{med_hist_codes_fn}) {
    $med_hist_codes = read_med_hist_codes_file($med_hist_codes_fh);
}

# read ID2NR translation table	
my $id2nr = {};
my $nfh = open_file($p->{id2nr_fn}, "r");
while (<$nfh>) {
	chomp;
	my ($id, $nr) = split(/\t/);
	# print "$_ : #$id,#$nr#\n";
	$id2nr->{$id} = $nr;
}
$nfh->close;
printf STDERR "Read %d id2nr records\n", scalar(keys %$id2nr);

# go over med records, extract registry entries and (optionally) med_hist entries
my $prev_nr = -1;
my $pat_recs;
while (<$med_fh>) {
    chomp;
    my $id = substr($_, 0, 10);
    $id =~ s/,//;
    next unless (exists $id2nr->{$id});
    my $nr = $id2nr->{$id};
    if ($nr != $prev_nr) {
		handle_single_pat($pat_recs, $prev_nr, 
				  $codes, $reg_fh,
				  $med_hist_codes, $med_hist_recs_fh) if ($prev_nr != -1);
		$prev_nr = $nr;
		$pat_recs = [];
    }
    push @$pat_recs, $_;
}
handle_single_pat($pat_recs, $prev_nr, 
		  $codes, $reg_fh,
		  $med_hist_codes, $med_hist_recs_fh) if ($prev_nr != -1);
$reg_fh->close;

die "Terminating after creation of Registry";

