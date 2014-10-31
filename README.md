# movistartv2xmltv 

Get *EPG* and *channels list* from multicast broadcast of *movistar tv*. Parse it
and generate *xmltv* for EPG and *M3U* for channels

You need to *setup dns 172.26.23.3* to resolve internals urls.

*Wired connection required*. UDP stream without any fix correction

## Integration with xmltv-util

Install xmltv-util and add sumbolic link to tv_grab_es_movistar.py in PATH

```
$ sudo apt-get install xmltv-util
$ pwd
 /home/multimedia/source/movistartv2xmltv
$ sudo ln -s /home/multimedia/source/movistartv2xmltv/tv_grab_es_movistar.py /usr/bin/
```
```
$ python tv_grab_es_movistar.py
usage: tv_grab_es_movistar.py [-h] [--description] [--capabilities] [--quiet]
                              [--output FILENAME] [--days GRAB_DAYS]
                              [--offset GRAB_OFFSET] [--m3u]

optional arguments:
  -h, --help            show this help message and exit
  --description         show 'Spain: Movistar IPTV grabber'
  --capabilities        show xmltv capabilities
  --quiet               Suppress all progress information. The grabber shall
                        only print error-messages to stderr.
  --output FILENAME     Redirect the xmltv output to the specified file.
                        Otherwise output goes to stdout.
  --days GRAB_DAYS      Supply data for X days. Grabber may have an upper
                        limit to the number of days that it can return data
                        for. If X is larger than that limit, the grabber shall
                        return no data for the days that it lacks data for,
                        print a warning to stderr, and exit with an error-
                        code. See XmltvErrorCodes. In other words, if too many
                        days are requested, the grabber will return data for
                        as many days as it can. The default number of days is
                        'as many as possible'
  --offset GRAB_OFFSET  Start with data for day today plus X days. The default
                        is 0, today; 1 means start from tomorrow, etc.
  --m3u                 Dump channels in m3u format
```

## Examples

Dump max days of epg to stdout

```sh	
 tv_grab_es_movistar
```

Dump 3 days of epg to epg.xml

```s
$ tv_grab_es_movistar --days 3 --output epg.xml
```

## TVheadend integration

M3U file is compatible with [m3u2hts](https://github.com/grudolf/m3u2hts)
You can use this tool to gen all channels and relationships with epg

```
$ tv_grab_es_movistar --m3u --output channels.m3u
$ python m3u2hts.py  -c utf-8 -r channels.m3u
```

Configuration files for tvheadend are in `/home/hts/.hts/tvheadend` and maybe you need to adjust permissions
