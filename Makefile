default:
	$(warning Choose compile, extract, init, or update!)

compile:
	pybabel compile -d domination/translations

extract:
	pybabel extract -F domination/domination.babelconfig -o domination/translations/messages.pot domination

update: extract
	pybabel update -i domination/translations/messages.pot -d domination/translations

init:
	echo Initing ${LANG} ...
	pybabel init -i domination/translations/messages.pot -d domination/translations -l ${LANG}


