#!/bin/bash

VERSION=`cat VERSION`
PKGNAME="funtoo-ramdisk"

prep() {
	install -d dist
	rm -f dist/$PKGNAME-$VERSION*
	cat > funtoo_ramdisk/version.py << EOF
__version__ = "$VERSION"
EOF
	for x in setup.py doc/manpage.rst; do
		sed -e "s/##VERSION##/$VERSION/g" \
		${x}.in > ${x}
	done
	rst2man.py doc/manpage.rst > doc/ramdisk.8
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
