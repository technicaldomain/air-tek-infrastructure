# show the message if not argument is passed
if [ -z "$1" ]
then
    echo "Please provide action to perform"
    echo "up, refresh, destroy"
    exit 1
fi

echo "This script is not respecting dependencies between stacks, use it with caution"

for d in ./*/
do
    if [ -f "$d/__main__.py" ]
    then
        echo "Running pulumi up in $d"
        # ls $d
        pulumi up -C $d -f
    fi
done
