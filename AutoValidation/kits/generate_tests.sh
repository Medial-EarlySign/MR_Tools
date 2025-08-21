#!/bin/bash
CURR_PT=$(realpath ${0%/*})
echo -e "Welcome to tests kit generation - please make sure you are in the folder you want to create those tests.\nCurrent Path: $PWD"

#check if we already have tests to avoid overrides/deleting work
HAS_RUN=$(ls -1 $PWD | egrep "^run.sh$" | wc -l)
if [ ${HAS_RUN} -gt 0 ]; then
	echo "Error - it seems like test kit already exists in this folder."
	echo "To recreate/override please erase ${PWD}/run.sh"
	exit 2
fi

echo "Please select KIT template"
ls -l ${CURR_PT} | egrep "^d" | awk '$NF!="resources" {print $NF}' | while  read -r KIT
do
	echo "##################################"
	echo "Option: \"${KIT}\""
	#cat README inside if exists
	if [ -f ${CURR_PT}/${KIT}/README ]; then
		echo -n "Description: "
		cat ${CURR_PT}/${KIT}/README
		echo ""
	fi
	echo -e "##################################"
done
read -p "Please enter valid option (or ctrl+c to cancel): " opt

FOUND=$(ls -l ${CURR_PT} | egrep "^d" | awk '{print $NF}' | egrep "^${opt}$" | wc -l)
if [ ${FOUND} -lt 1 ]; then
	echo "Please selecte valid option - failed"
	exit 1
fi

echo -e "#!/bin/bash\n\${AUTOTEST_LIB}/autotest ${opt} \$1" > run.sh
echo -e "#!/bin/bash\n\${AUTOTEST_LIB}/autotest.specific_test ${opt} \$1" > run.specific_test.sh

mkdir -p Tests
#copy template config
cp -r ${CURR_PT}/${opt}/configs configs
cp -r ${CURR_PT}/resources/Templates Tests/Templates

echo "You can override/add tests in ${PWD}/Tests"
echo "You are all done - to run tests - please use ${PWD}/run.sh"