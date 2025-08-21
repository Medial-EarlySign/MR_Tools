for i in Fixed/*; do
   #echo "test $i"
   sort -n -k1 -c -s $i
done
