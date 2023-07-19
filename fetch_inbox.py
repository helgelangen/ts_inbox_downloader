# coding=utf-8
from pathlib import Path
import httpx
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
import re
import sys

try:
   from cilogger.cilogger import ciLogger
except ModuleNotFoundError:
   print( "Submoduler er ikke oppdatert" )
   print( "Dersom du har brukt git for å hente scriptet, prøv å kjøre kommandoen" )
   print( "git submodule update --init")
   sys.exit(1)

def main():

   term = ciLogger()
   term.colFormat = "timer:runtime:3:10;80"
   
   logDate = datetime.now().strftime( "%Y-%m-%d %H:%M" )
   term.ciPrint(" ")
   term.ciDebug( "===============================================================")
   term.ciDebug( f"Terrengsykkelforumet meldingsnedlaster startet {logDate}" )
   term.ciDebug( "===============================================================")
   term.ciPrint( " ")
   
   secretFile = Path( "secret.json")
   
   # Sjekk secret-filen etter beste evne
   if ( secretFile.is_file() ):
   
      with open( secretFile, "r" ) as inputFp:
         secrets = json.load( inputFp )
         inputFp.close()
         
      if ( "terrubbt_myid" in secrets and "terrubbt_hash" in secrets and "terrubbt_mysess" in secrets ):
         if ( ( len( secrets["terrubbt_myid"] ) == 4 or len( secrets["terrubbt_myid"] ) == 5 ) and len( secrets["terrubbt_hash"] ) == 32 and len( secrets["terrubbt_mysess"] ) == 32 ):
            if ( secrets["terrubbt_myid"] == "99999" or secrets["terrubbt_hash"] == "1234567890abcdef1234567890abcdef" or secrets["terrubbt_mysess"] == "1234567890abcdef1234567890abcdef" ):
               term.ciError( "En eller flere av verdiene i secret.json er standardverdier. Vennligst endre til dine riktige verdier" )
               sys.exit(1)
         else:
            term.ciError( "Feil lengde på noen av verdiene i secret.json. Vennligst sjekk at innholdet er riktig" )
            sys.exit(1)
      else:
         term.ciError( "En eller flere verdier i secret.json mangler. Vennligst sjekk at innholdet er riktig" )
         sys.exit(1)
   else:
      term.ciError( "Fant ikke filen secret.json som er nødvendig for å logge inn. Scriptet avsluttes" )
      sys.exit(1)
   
   # Sett cookies for innlogging
   cookies = httpx.Cookies()
   cookies.set("redirect_visited", "true", domain="www.terrengsykkelforumet.no")
   cookies.set("redirect_visited_new_new", "true", domain="www.terrengsykkelforumet.no")
   cookies.set("terrubbt_myid", secrets["terrubbt_myid"],  path="/", domain="www.terrengsykkelforumet.no")
   cookies.set("terrubbt_hash", secrets["terrubbt_hash"], path="/", domain="www.terrengsykkelforumet.no")
   cookies.set("terrubbt_mysess", secrets["terrubbt_mysess"], path="/", domain="www.terrengsykkelforumet.no")

   client = httpx.Client()

   jsonLogPath = Path( "inbox_fetchlog.json" )

   if ( jsonLogPath.is_file() ):

      with open( jsonLogPath, "r" ) as inputFp:
         jsonLog = json.load( inputFp )
         inputFp.close()

   else:
      jsonLog = {}

   fetchUrl = "https://www.terrengsykkelforumet.no/ubbthreads.php?ubb=viewmessages"

   # Opprett mapper for å lagre de nedlastede meldingene og meldingsoversikten dersom de ikke eksisterer
   Path( "fetched_messages" ).mkdir( parents=True, exist_ok=True )
   Path( "fetched_messages", "threads" ).mkdir( parents=True, exist_ok=True )

   # Logg til en json-fil
   jsonLog[logDate] = { "inboxpages": 0, "threads": 0, "pages": 0, "messages": 0, "finishDate": logDate}

   page = 1
   totPages = 1
   
   threads = {}
   loginProblemRe = re.compile( "Et problem oppstod.  Grunnen som ble rapportert var" )

   # Last ned første side av innboksen
   r = client.get( fetchUrl, cookies=cookies)
   r.encoding = "iso-8859-1"

   if ( r.status_code == 200 ):

      jsonLog[logDate]["inboxpages"] += 1
      with open( Path( "fetched_messages", f"innboks_{page:03d}.htm" ), "w" ) as inboxFp:
         inboxFp.write( r.text )
         inboxFp.close()
      
      if ( loginProblemRe.search( r.text ) ):
         term.ciError( "Innlogging feilet. Vennligst sjekk at informasjonen i secret.json er riktig" )
         sys.exit(1)
      
      soup = BeautifulSoup( r.text, "html.parser" )
      
      if ( displayNameSearch := soup.find( "div", class_ = "my-displayname") ):
         if ( userLink := displayNameSearch.find( "a" ) ):
            displayName = userLink.decode_contents()
            if ( len( displayName ) ):
               term.ciInfo( f"Innlogget som {displayName}" )
   
      tmpThreads = parseThreadPage( r.text, term )
      term.ciInfo( f"Fant {len(tmpThreads)} meldingstråder på side {page}")
      jsonLog[logDate]["threads"] += len(tmpThreads)
      threads.update( tmpThreads )
   
      if ( pageCounter := soup.find( "td", class_ = "pages acvm nw" ) ):
         if ( pageCounterSearch := re.search( ">[\s]*Side[\s]*1[\s]*av[\s]*([0-9]{1,3})[\s]*<", str( pageCounter ) ) ):
            totPages = int( pageCounterSearch.group(1) )
      
   else:
      term.ciError( f"Kunne ikke laste ned innboks for bruker {myId}. Statuskode {r.status_code}" )

   for page in range( 2, totPages+1):

      fetchUrl = f"https://www.terrengsykkelforumet.no/ubbthreads.php?ubb=viewmessages&page={page}"
   
      r = client.get( fetchUrl, cookies=cookies)
      r.encoding = "iso-8859-1"

      if ( r.status_code == 200 ):
   
         jsonLog[logDate]["inboxpages"] += 1
         with open( Path( "fetched_messages", f"innboks_{page:03d}.htm" ), "w" ) as inboxFp:
            inboxFp.write( r.text )
            inboxFp.close()
      
         tmpThreads = parseThreadPage( r.text, term )
         term.ciInfo( f"Fant {len(tmpThreads)} meldingstråder på side {page}")
         jsonLog[logDate]["threads"] += len(tmpThreads)
         threads.update( tmpThreads )
   
      finishDate = datetime.now().strftime( "%Y-%m-%d %H:%M" )
      jsonLog[logDate]["finishDate"] = finishDate
      with open( jsonLogPath, "w" ) as inputFp:
         inputFp.write( json.dumps( jsonLog, indent=3, ensure_ascii=False ) )
         inputFp.close()
   
      # Litt throttling for å ikke kræsje serveren
      time.sleep(0.2)
   
   term.ciInfo( "Laster ned innholdet i meldingstrådene, dette kan ta noen minutter. Vennligst vent" )
   
   for thread in threads.values():
   
      page = 1
   
      fetchUrl = f"https://www.terrengsykkelforumet.no/ubbthreads.php?ubb=viewmessage&message={thread['threadId']}"
      
      r = client.get( fetchUrl, cookies=cookies) # headers=headers, 
      r.encoding = "iso-8859-1"

      if ( r.status_code == 200 ):
      
         with open( Path( "fetched_messages", "threads", f"melding_{thread['threadId']}_{page:03d}.htm" ), "w" ) as inboxFp:
            inboxFp.write( r.text )
            inboxFp.close()
         
         jsonLog[logDate]["pages"] += 1
         
         tmpTitle, tmpPosts = parseMessagePage( r.text, term )
         threads[ thread["threadId"] ]["title"] = tmpTitle
         threads[ thread["threadId"] ]["posts"] = tmpPosts
         jsonLog[logDate]["messages"] += len( tmpPosts )
         
         if ( "pages" in thread ):
         
            for page in range( 2, thread["pages"] + 1 ):
            
               fetchUrl = f"https://www.terrengsykkelforumet.no/ubbthreads.php?ubb=viewmessage&message={thread['threadId']}&page={page}"
               
               r = client.get( fetchUrl, cookies=cookies) # headers=headers, 
               r.encoding = "iso-8859-1"

               if ( r.status_code == 200 ):
               
                  jsonLog[logDate]["pages"] += 1
                  tmpTitle, tmpPosts = parseMessagePage( r.text, term )
                  threads[ thread["threadId"] ]["posts"].update( tmpPosts )
                  jsonLog[logDate]["messages"] += len( tmpPosts )
      
                  with open( Path( "fetched_messages", "threads", f"melding_{thread['threadId']}_{page:03d}.htm" ), "w" ) as inboxFp:
                     inboxFp.write( r.text )
                     inboxFp.close()
               
               time.sleep(0.2)
         
         finishDate = datetime.now().strftime( "%Y-%m-%d %H:%M" )
         jsonLog["finishDate"] = finishDate
         with open( jsonLogPath, "w" ) as inputFp:
            inputFp.write( json.dumps( jsonLog, indent=3, ensure_ascii=False ) )
            inputFp.close()
   
   term.ciSuccess( f"Lastet ned {jsonLog[logDate]['threads']} meldingstråder med {jsonLog[logDate]['messages']} meldinger på {jsonLog[logDate]['pages']} sider, {jsonLog[logDate]['inboxpages']} sider med liste over meldingstråder" )
   
   term.ciInfo( "Lagrer data i inbox.json" )
   with open( Path( "inbox.json" ), "w") as outputFp:
      outputFp.write( json.dumps( threads, indent=3, ensure_ascii=False) )
      outputFp.close()

   
def parseThreadPage( s, term ):

   soup = BeautifulSoup( s, "html.parser" )
   
   postRowRe = re.compile( "^postrow-inline-" )
   threadTitleRe = re.compile( "ubb=viewmessage(&|&amp;)message=([0-9]{1,8})" )
   threadStarterRe = re.compile( "ubb=showprofile(&|&amp;)User=([0-9]{4,5})" )
   threadMultiPagesRe = re.compile( "ubb=viewmessage(&|&amp;)message=([0-9]{1,8})&page=([0-9]{1,4})")
   participantsRe = re.compile( "Deltagere:[\s]*<\/span>[\s]*(.*?)[\s]*<")
   
   topicRepliesRe = re.compile( "^(new-t|alt-t|t)opicreplies" )
   topicLastPostRe = re.compile( "^(new-t|alt-t|t)opicviews")
   
   postRows = soup.find_all( "tr", id = postRowRe )
   
   threads = {}
   
   for postRow in postRows:
   
      tmpThread = {}
      
      if ( titleHref := postRow.find( "a", { "href": threadTitleRe } ) ):
         tmpThread["title"] = titleHref.decode_contents()
         if ( idSearch := threadTitleRe.search( str( titleHref ) ) ):
            tmpThread["threadId"] = idSearch.group(2)
      
      if ( starterHref := postRow.find( "a", { "href": threadStarterRe})):
         tmpThread["startedBy"] = parseNameTag( starterHref.decode_contents() )
         if ( idSearch := threadStarterRe.search( str( starterHref ) ) ):
            tmpThread["startedBy"]["userId"] = idSearch.group(2)
      
      if ( multiPageHrefs := postRow.find_all( "a", { "href": threadMultiPagesRe } ) ):
         tmpThread["pages"] = int( multiPageHrefs[-1].decode_contents() )
      
      if ( participantSearch := participantsRe.search( str( postRow ) ) ):
         tmpThread["participants"] = participantSearch.group(1).strip().split(", ")
      
      if ( repliesSearch := postRow.find( "td", class_ = topicRepliesRe ) ):
         tmpThread["replies"] = repliesSearch.decode_contents().strip()
      
      if ( lastPostSearch := postRow.find( "td", class_ = topicLastPostRe ) ):
         if ( postDate := lastPostSearch.find( "span", class_ = "date" ) ):
            tmpThread["lastPostDate"] = postDate.decode_contents()
         if ( postTime := lastPostSearch.find( "span", class_ = "time" ) ):
            tmpThread["lastPostDate"] += " " + postTime.decode_contents()
      
      if ( "threadId" in tmpThread ):
         threads[ tmpThread["threadId"] ] = tmpThread
   
   return threads

def parseMessagePage( s, term ):

   postAuthorRe = re.compile( "ubb=showprofile(&|&amp;)User=([0-9]{4,5})" )
   registeredRe = re.compile( ">[\s]*Registrert:[\s]*([0-9]{2}\/[0-9]{2}\/[0-9]{4})[\s]*<" )
   totalPostsRe = re.compile( ">[\s]*Innlegg:[\s]*([,0-9]{1,6})[\s]*<" )
   authorLocationRe = re.compile( ">[\s]*Sted:[\s]*(.*?)[\s]*<" )
   
   bodyIdRe = re.compile( "^body" )
   signatureRe = re.compile( "^signature" )
   postIdRe = re.compile( "id=\"number([0-9]{1,8})\">[\s]*#([0-9]{1,8})[\s]*<" )
   
   unreadRe = re.compile( "Ulest av:[\s]*<\/span>[\s]*(.*?)[\s]*<")
   
   soup = BeautifulSoup( s, "html.parser" )
   
   posts = {}
   title = ""
   
   if ( heading := soup.find( "h1" ) ):
      title = heading.decode_contents()
   
   postRows = soup.find_all( "table", class_ = "t_inner hardlyWidth" )
   
   for postRow in postRows:
   
      tmpPost = { "author": {} }
      if ( registeredSearch := registeredRe.search( str( postRow ) ) ):
         tmpPost["author"]["registered"] = registeredSearch.group(1)
         
         if ( authorSearch := postRow.find( "a", {"href": postAuthorRe }, class_ = "bold" ) ):
            tmpPost["author"].update( parseNameTag( authorSearch.decode_contents() ) )
            if ( idSearch := postAuthorRe.search( str( authorSearch ) ) ):
               tmpPost["author"]["userId"] = idSearch.group(2)
         
         if ( postCountSearch := totalPostsRe.search( str( postRow ) ) ):
            tmpPost["author"]["totalPosts"] = postCountSearch.group(1)
         
         if ( locationSearch := authorLocationRe.search( str( postRow ) ) ):
            tmpPost["author"]["location"] = locationSearch.group(1)
         
         if ( subjectRow := postRow.find( "td", class_ = "subjecttable" ) ):
            if ( subjectSearch := subjectRow.find( "span", class_ = "bold" ) ):
               tmpPost["title"] = subjectSearch.decode_contents()
            if ( postIdSearch := postIdRe.search( str( subjectRow ) ) ):
               tmpPost["postId"] = postIdSearch.group(2)
            if ( postDate := subjectRow.find( "span", class_ = "date" ) ):
               tmpPost["postedDate"] = postDate.decode_contents()
            if ( postTime := subjectRow.find( "span", class_ = "time" ) ):
               tmpPost["postedDate"] += " " + postTime.decode_contents()
         
         if ( bodySearch := postRow.find( "div", { "id": bodyIdRe } ) ):
            tmpPost["text"] = bodySearch.decode_contents()
         
         if ( signatureSearch := postRow.find( "div", class_ = signatureRe ) ):
            tmpPost["author"]["signature"] = signatureSearch.decode_contents().replace("<hr class=\"signature\"/>", "").strip()
         
         if ( unreadSearch := unreadRe.search( str( postRow ) ) ):
            tmpPost["unreadBy"] = unreadSearch.group(1)
         
         if ( "postId" in tmpPost ):
            posts[ tmpPost["postId"] ] = tmpPost
   
   return title, posts


def parseNameTag( s ):

   adminNameRe = re.compile( "<span class=\"adminname\">(.*?)<\/span>" )
   globalModNameRe = re.compile( "<span class=\"globalmodname\">(.*?)<\/span>" )
   modNameRe = re.compile( "<span class=\"modname\">(.*?)<\/span>" )
   
   tmpUser = {}
   
   if ( adminPosterSearch := adminNameRe.search( s ) ):
      tmpUser["Admin"] = True
      tmpUser["Name"] = adminPosterSearch.group(1)
   elif ( adminPosterSearch := globalModNameRe.search( s ) ):
      tmpUser["GlobalModerator"] = True
      tmpUser["Name"] = adminPosterSearch.group(1)
   elif ( adminPosterSearch := modNameRe.search( s ) ):
      tmpUser["Moderator"] = True
      tmpUser["Name"] = adminPosterSearch.group(1)
   else:
      tmpUser["Name"] = s
   
   return tmpUser
         

if __name__ == '__main__':
    main()
   