pip install cldfbench
pip install pyglottolog pyconcepticon pyclts

{
    # If you want control over the download size of the catalog repositories, do
    # this. Otherwise, catconfig downloads the whole history of each catalog, which
    # is huge in particular for Glottolog!!!
    cd ~/.config/cldf/
    git clone --depth 1 git@github.com:glottolog/glottolog.git
    git clone --depth 1 git@github.com:concepticon/concepticon-data.git
    git clone --depth 1 git@github.com:cldf-clts/clts.git
}

cldfbench catconfig
cldfbench catinfo
