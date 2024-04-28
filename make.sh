#!/bin/bash

VERSION=`cat VERSION`
PKGNAME="funtoo-ramdisk"
LASTYEAR=`date +%Y`

prep() {
	install -d dist
	rm -f dist/$PKGNAME-$VERSION*
	cat > funtoo_ramdisk/version.py << EOF
__version__ = "$VERSION"
EOF
	for x in setup.py doc/manpage.rst; do
		sed -e "s/##VERSION##/$VERSION/g" -e "s/##LASTYEAR##/$LASTYEAR/g" \
		${x}.in > ${x}
	done
	if [ -n "$( which rst2man.py 2>/dev/null )" ]; then
		rst2man.py doc/manpage.rst > doc/ramdisk.8
		[ $? -ne 0 ] && echo "man page fail" && exit 1
	elif [ -n "$( which rst2man 2>/dev/null )" ]; then
		rst2man doc/manpage.rst > doc/ramdisk.8
		[ $? -ne 0 ] && echo "man page fail" && exit 1
	else
		echo "rst2man(.py) not found. Please install docutils."
		exit 1
	fi
}

commit() {
	git commit -a -m "$PKGNAME $VERSION release."
	git tag -f "$VERSION"
	git push
	git push --tags -f
	python3 setup.py sdist
}

if [ "$1" = "prep" ]
then
	prep
elif [ "$1" = "commit" ]
then
	commit
elif [ "$1" = "all" ]
then
	prep
	commit
elif [ "$1" = "amend" ]
then
	prep
	git commit -a --amend
	git tag -f "$VERSION"
	git push -f
	git push --tags -f
	python3 setup.py sdist
fi
