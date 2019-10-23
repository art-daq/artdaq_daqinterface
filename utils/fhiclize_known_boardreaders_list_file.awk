
{

    if ($0 ~ /^\s*#/ ) {
	next
    }

    if ($0 ~ /^\s*$/ ) {
	next
    }

    printf("%s: [", $1);
    for (i = 2; i <= NF; ++i) {
	printf("\"%s\"", $i);

	if (i != NF) {
	    printf(", ");
	} else {
		printf("]\n"); 
	}
    }
}
