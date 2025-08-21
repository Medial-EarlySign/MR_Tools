#include "MedUtils/MedUtils/MedMedical.h"
#include "Catch-master/single_include/catch.hpp"

TEST_CASE("eGFR calculations", "[egfr]") {
	REQUIRE(get_eGFR_MDRD(0, 0.24, 1) == -1); // age is less than 1
	REQUIRE(get_eGFR_MDRD(30, 0.01, 1) == -1); // creatinine is less than 0.1
}
