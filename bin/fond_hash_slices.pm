#
# The following hash aggregates fund names that have changed over time
#
# Fund names must be in lower case
%fund_names = (
	'ab american growth a $' => [
		'ab american growth a $',
		"ab american growth a usd",
		"acm american growth a usd",
		'acm american growth a $',
		"alliance capital american growth"
	],
	'ab global growth trends a $' => [
		'ab global growth trends a $',
		'acm global growth trends a $',
		"alliance capital glob grow trend"
		
	],
	'ab international tech fund a $' => [
		'ab international tech fund a $',
		'ab international tech fund a$',
		'acm international tech fund a$',
		"alliance capital int technology"
	],
	"alliancebernstein amer val a usd" => [
		"alliancebernstein amer val a usd",
		"acm bernstein american value"
	],
	"alterum global quality growth" => [
		"alterum global quality growth",
		"fmg alterum gl quality",
		"fmg alterum mir glob quality gr",
		"fmg gl quality"
	],
	"baring north america" => [
		"baring north america",
		"baring north america fund (usd)"
	],
	"blackrock european" => [
		"blackrock european",
		"merrill lynch european"
	],
	"blackrock global equity" => [
		"blackrock global equity",
		"merrill lynch global equity",
		"mercury st global equity"
	],
	"blackrock global opportun" => [
		"blackrock global opportun",
		"mercury global opportun (usd)",
		"mercury st global opportunitie",
		"merrill lynch global opportun"
	],
	"blackrock global small cap p" => [
		"blackrock global small cap p",
		"merrill lynch global small cap p"
	],
	"blackrock japan opportunitie" => [
		"blackrock japan opportunitie",
		"mercury japan opportfund(usd)",
		"mercury japan opps(usd)",
		"mercury japop usd",
		"mercury st japan opportunities",
		"merrill lynch japan opportunitie"
	],
	"blackrock latin america a2" => [
		"blackrock latin america a2",
		"merrill lynch latin america a2"
	],
	"carnegie east european" => [
		"carnegie east european",
		'carnegie east ?opean'
	],
	"east capital ryssland" => [
		"east capital ryssland",
		"east capital ryssland sek",
		"east capital rysslandsfond"
	],
	"fidelity asian special" => [
		"fidelity asian special",
		"fidelity asian special (usd)"
	],
	"fidelity australia" => [
		"fidelity australia",
		"fidelity australia (aud)"
	],
	"fidelity euro growth" => [
		"fidelity euro growth",
		"fidelity european growth"
	],
	"fidelity euro small" => [
		"fidelity euro small",
		"fidelity european small"
	],
	"fidelity france" => [
		"fidelity france",
		"fidelity france (eur)"
	],
	"fidelity germany" => [
		"fidelity germany",
		"fidelity germany (eur)"
	],
	"fidelity iberia" => [
		"fidelity iberia",
		"fidelity iberia (eur)"
	],
	"fidelity italy" => [
		"fidelity italy",
		"fidelity italy (eur)"
	],
	"goldman brics portfol eur e cap" => [
		"goldman brics portfol eur e cap",
		"goldman bric pf euro hedged base"
	],
	"goldman sachs global high yield" => [
		"goldman sachs global high yield",
		"goldman sachs hiyi e hedge"
	],
	"gartmore gl focus fund" => [
	"gartmore gl focus fund",
	"gartmore global focus fund"
	],
	"jf china fund a" => [
		"jf china fund a",
		"jpmf china a",
		"jp morgan fleming jf china",
		"jpmorgan fleming china a",
		"fleming china",
		"fleming china (usd)",
		"fleming china(usd)"
	],
	"jf pacific equity a" => [
		"jf pacific equity a",
		"jpmf pacific equity a",
		"jp morgan fleming jf pacific",
		"jpmorgan fleming pacific eq a",
	],
	"jpm gbl natural resources a acc" => [
		"jpm gbl natural resources a acc",
		"jpm gbl natural resources aacc"
	],
	"pictet biotech p" => [
		"pictet biotech p",
		"pictet biotech p (usd)"
	],
	"schroder asian bond a" => [
		"schroder asian bond a",
		"schroders asian bond a (usd)"
	],
	"schroder emerging europe a acc" => [
		"schroder emerging europe a acc",
		"schroders emerging europe dis a",
		"schroder emerging europe acc a",
		"schroder emerging europe dis a"
	],
	"schroder emerging mkt debt a acc" => [
		"schroder emerging mkt debt a acc",
		"schroder emerging markets deb ac",
		"schroder emerging markets dept",
		"schroders emer markdept (usd)"
	],
	"seb a asien" => [
		"seb a asien",
		"seb a asienfond"
	],
	"seb a f-anknuten allemansfond" => [
		"seb a f-anknuten allemansfond",
		"seb a f-ankn allf",
		"abb f-anknuten allemansfond",
		"seb abb f-anknuten allemansfond"
	],
	"seb a global obl" => [
		"seb a global obl",
		"seb a global obligationsfond"
	],
	"seb a schweiz" => [
		"seb a schweiz",
		"seb a schweizfond"
	],
	"seb a sverige" => [
		"seb a sverige",
		"seb a sverige (fd aktiefond)"
	],
	"seb a total" => [
		"seb a total",
		"seb a totalfond"
	],
	"seb a usa" => [
		"seb a usa",
		"seb a usa fond",
		"seb a usa-fond"
	],
	"seb aktiespar" => [
		"seb aktiespar",
		"seb aktiesparfond"
	],
	"seb allemansfond aktier" => [
		"seb allemansfond aktier",
		"seb allemansfond aktiespar"
	],
	"seb allemansfond norden" => [
		"seb allemansfond norden",
		"seb norden"
	],
	"seb alpha bond sek d - lux utd" => [
		"seb alpha bond sek d - lux utd",
		"seb alpha bond d - lux utd",
		"seb oblfond europa - lux utd",
		"seb oblfond europa usd - lux utd",
		"seb lux bond fund europe inc",
		"seb lux europe bond fund inc",
		"seb skandifond europe bond inc"
	],
	"seb ch asien små x j - lux ack" => [
		"seb ch asien små x j - lux ack",
		"seb co asien x j små - lux ack",
		"seb asien ex jap småb - lux ack",
		"seb lux cs asian small co",
		"seb a asien småbol",
		"seb a asien småbolag",
		"seb a asien småbolagsfond",
		"seb a asienf småbolag"
	],
	"seb choice asienfond ex japan" => [
		"seb choice asienfond ex japan",
		"seb asienfond ex japan",
		"seb asien ex japan",
		"seb asien (exkl japan)",
		"seb asienfond",
		"seb asienfond (exkl japan)",
		"seb horisontfond"
	],
	"seb ch asien x jap - lux ack" => [
		"seb ch asien x jap - lux ack",
		"seb co asien x jap - lux ack",
		"seb asienfond ex japan - lux ack",
		"seb asien ex japan - lux ack",
		"seb skandifond far east",
		"seb lux asia fund",
		"seb lux asia fund - ex japan",
		"seb lux asia fund - global"
	],
	"seb ch asien x jap - lux utd" => [
		"seb ch asien x jap - lux utd",
		"seb co asien x jap - lux utd",
		"seb asienfond ex japan - lux utd",
		"seb asien ex japan - lux utd",
		"seb lux fund asia equity",
		"seb lux (f) asien (exkl japan)",
		"seb fund fjÖstern",
		"seb fund fjärran Östern"
	],
	"seb baltikumfond - lux ack" => [
		"seb baltikumfond - lux ack",
		"seb lux cs baltic smaller comp",
		"seb a Östersjö småbolagsfond",
		"seb a Östersjö små",
		"seb a Östersjö småbolag",
		"seb a Östersjö småbolagsfond"
	],
	"seb bioteknikfond - lux ack" => [
		"seb bioteknikfond - lux ack",
		"seb invest concept biotechnology"
	],
	"seb cancerfond" => [
		"seb cancerfond",
		"seb cancerfonden"
	],
	"seb corporate bond eur - lux ack" => [
		"seb corporate bond eur - lux ack",
		"seb lux bond corp bond eur acc",
		"seb lux bond corp bonds eur acc"
	],
	"seb corporate bond eur - lux utd" => [
		"seb corporate bond eur - lux utd",
		"seb lux bond corp bond eur inc",
		"seb lux bond corp bonds eur inc"
	],
	"seb corporate bond sek - lux ack" => [
		"seb corporate bond sek - lux ack",
		"seb lux bond corp bond sek acc",
		"seb lux bond corp bonds sek acc"
	],
	"seb corporate bond sek - lux utd" => [
		"seb corporate bond sek - lux utd",
		"seb lux bond corp bond sek inc",
		"seb lux bond corp bonds sek inc"
	],
	"seb choice emerging markets" => [
		"seb choice emerging markets",
		"seb emerg market",
		"seb emerging mark",
		"seb emerging markets",
		"seb emerging markets fund",
		"seb emerging marketsfond"
	],
	"seb ch emerging mark - lux ack" => [
		"seb ch emerging mark - lux ack",
		"seb co emerging mark - lux ack",
		"seb emerging markets - lux ack",
		"seb lux emerging markets fund",
		"seb skandifond emerg markets"
	],
	"seb etisk europafond - lux ack" => [
		"seb etisk europafond - lux ack",
		"seb lux equity ethical europe",
		"seb lux equity euro markets 3",
		"seb lux equity mediterranean",
		"seb lux mediterranean fund",
		"seb skandifond mediterranean"
	],
	"seb etisk globalfond" => [
		"seb etisk globalfond",
		"seb miljÖfond",
		"seb miljöfond"
	],
	"seb etisk globalfond - lux utd" => [
		"seb etisk globalfond - lux utd",
		"seb lux fund ethical global",
		"seb lux (f) miljÖfond",
		"seb lux (f) miljöfond",
		"seb fund miljö"
	],
	"seb etisk sverigefond - lux utd" => [
		"seb etisk sverigefond - lux utd",
		"seb lux (f) sverige",
		"seb lux (f) sverige offensivfond",
		"seb lux (f) sverigefond",
		"seb lux fund ethical sweden",
		"seb fund sverige"
	],
	"seb europa" => [
		"seb europa",
		"seb europafond"
	],
	"seb europa småbolag - lux utd" => [
		"seb europa småbolag - lux utd",
		"seb europa småbolag - lux ack",
		"seb invest neue märkte",
		"seb lux bfg neue märkte"
	],
	"seb europa chans risk - lux ack" => [
		"seb europa chans risk - lux ack",
		"seb lux cs europe chance risk",
		"seb a euro equity",
		"seb a euro equity (eur)",
		"seb a european equity fund"
	],
	"seb europafond småbolag" => [
		"seb europafond småbolag",
		"seb eur småbolag",
		"seb europa småbolag",
		"seb europa småbolagsfond",
		"seb europeiska småbolagsfo",
		"seb europeiska småbolagsfond"
	],
	"seb europafond 1 - lux ack" => [
		"seb europafond 1 - lux ack",
		"seb europafond 1- lux ack",
		"seb euro marketsfond 1- lux ack",
		"seb lux equity euro markets 1",
		"seb lux eq continental europe",
		"seb lux continental europe",
		"seb skandifond contin europe"
	],
	"seb europafond 2 - lux ack" => [
		"seb europafond 2 - lux ack",
		"seb euro marketsfond 2 - lux ack",
		"seb lux equity euro markets 2",
		"seb lux equity fund euroland",
		"seb lux euro equity fund",
		"seb skandifond equ fund euro"
	],
	"seb europafond 3 - lux ack" => [
		"seb europafond 3 - lux ack",
		"seb uk - lux ack",
		"seb lux equity united kingdom",
		"seb lux united kingdom fund",
		"seb skandifond united kingdom"
	],
	"seb europafond - lux utd" => [
		"seb europafond - lux utd",
		"seb europa - lux utd",
		"seb lux fund europe equity",
		"seb lux (f) europafond",
		"seb fund europa"
	],
	"seb fjärran Östern" => [
		"seb fjärran Östern",
		"seb fjärran Östernfond"
	],
	"seb forskningsfond sv läk sällsk" => [
		"seb forskningsfond sv läk sällsk",
		"seb forskning",
		"seb forskningsfond"
	],
	"seb fund sv räntef" => [
		"seb fund sv räntef",
		"seb fund sv räntefond"
	],
	"seb global" => [
		"seb global",
		"seb globalfond",
		"seb a global",
		"seb a globalfond"
	],
	"seb global chans risk - lux ack" => [
		"seb global chans risk - lux ack",
		"seb lux eq global chans risk",
		"seb global chans risk"
	],
	"seb globalfond - lux ack" => [
		"seb globalfond - lux ack",
		"seb global - lux ack",
		"seb lux equity fund global",
		"seb lux global fund",
		"seb skandifond global"
	],
	"seb globalfond - lux utd" => [
		"seb globalfond - lux utd",
		"seb global - lux utd",
		"seb lux fund global equity",
		"seb lux (f) globalfond",
		"seb fund global"
	],
	"seb ch global value - lux ack" => [
		"seb ch global value - lux ack",
		"seb co global value - lux ack",
	 	"seb global value - lux ack",
	 ],
	"seb ch global value - lux utd" => [
		"seb ch global value - lux utd",
		"seb co global value - lux utd",
	 	"seb global value - lux utd",
	 ],
	"seb hedgefond" => [
		"seb hedgefond",
		"seb hedgefond equity",
		"trygg penningmarknadsfond",
		"trygg penningmfon"
	],
	"seb internat blandfond - lux ack" => [
		"seb internat blandfond - lux ack",
		"seb lux equity international acc",
		"seb lux international fund acc",
		"seb skandifond intacc"
	],
	"seb internat blandfond - lux utd" => [
		"seb internat blandfond - lux utd",
		"seb lux equity international inc",
		"seb lux international fund inc",
		"trygg mixed fund"
	],
	"seb internet" => [
		"seb internet",
		"seb internet fond",
		"seb internetfond"
	],
	"seb ireland bond fund" => [
		"seb ireland bond fund",
		"seb (ireland) bond fund",
		"trygg bond fund"
	],
	"seb ireland equity fund" => [
		"seb ireland equity fund",
		"seb (ireland) equity fund",
		"trygg equity fund"
	],
	"seb ireland finnish global eq" => [
		"seb ireland finnish global eq",
		"seb (ireland) finnish equity",
		"seb (ireland) finnish global eq",
		"trygg finnish eq",
		"trygg finnish equity fund"
	],
	"seb ireland mixed fund" => [
		"seb ireland mixed fund",
		"seb (ireland) mixed fund",
		"seb skandifond intinc"
	],
	"seb choice japanfond" => [
		"seb choice japanfond",
		"seb japan",
		"seb japanfond"
	],
	"seb ch japan c r - lux ack"  => [
		"seb ch japan c r - lux ack",
		"seb co japan c r - lux ack",
		"seb japan chans risk - lux ack",
		"seb lux equity japan chans risk"
	],
	"seb ch japanfond c - lux ack" => [
		"seb ch japanfond c - lux ack",
		"seb co japanfond c - lux ack",
		"seb japanfond c - lux ack",
		"seb japanfond - lux ack",
		"seb japan - lux ack",
		"seb lux equity fund japan",
		"seb lux japan fund",
		"seb skandifond japan"
	],
	"seb ch japanfond d - lux utd" => [
		"seb ch japanfond d - lux utd",
		"seb co japanfond d - lux utd",
		"seb japanfond d- lux utd",
		"seb japanfond - lux utd",
		"seb japan - lux utd",
		"seb lux fund japan equity",
		"seb lux (f) japanfond",
		"seb fund japan"
	],
	"seb klar placeringsfond" => [
		"seb klar placeringsfond",
		"seb trygg klar placeringsfond",
		"trygg klar placer",
		"trygg klar placering",
		"trygg klar placeringsfond"
	],
	"seb choice latinamerika" => [
		"seb choice latinamerika",
		"seb latinamerika",
		"seb latinamerikafond"
	],
	"seb life - asia equity" => [
		"seb life - asia equity",
		"seb life asien (exkl japan)",
		"seb life asienfond (exkl japan)",
		"seb life fund asia equity",
		"seb life asien (exkl japan)",
		"seb life fjärran Östern",
		"seb life fj Östern"
	],
	"seb life - emerging markets" => [
		"seb life - emerging markets",
		"seb life emerging marketsfond"
	],
	"seb life - ethical global" => [
		"seb life - ethical global",
		"seb life fund ethical global",
		"seb life miljÖfond",
		"seb life miljö",
		"seb life miljöfond"
	],
	"seb life - ethical sweden" => [
		"seb life - ethical sweden",
		"seb life fund ethical sweden",
		"seb life sverige",
		"seb life sverige offensivfond"
	],
	"seb life - europa småbolag" => [
		"seb life - europa småbolag",
		"seb life europa småbolagsfond"
	],
	"seb life - europe equity" => [
		"seb life - europe equity",
		"seb life fund europe equity",
		"seb life europa",
		"seb life europafond"
	],
	"seb life - global equity" => [
		"seb life - global equity",
		"seb life fund global equity",
		"seb life global",
		"seb life globalfond"
	],
	"seb life - index linked bond" => [
		"seb life - index linked bond",
		"seb life fund index linked bond",
		"seb life avkastningsfond",
		"seb life avkastnf",
		"seb life fund swe medium term"
	],
	"seb life - internet" => [
		"seb life - internet",
		"seb life internet",
		"seb life internetfond"
	],
	"seb life - japan equity" => [
		"seb life - japan equity",
		"seb life fund japan equity",
		"seb life japan",
		"seb life japanfond"
	],
	"seb life - latinamerikafond" => [
		"seb life - latinamerikafond",
		"seb life latinamerikafond",
	],
	"seb life - medical" => [
		"seb life - medical",
		"seb life fund medical",
		"seb life läkemedel",
		"seb life läkemedel- & bioteknik"
	],
	"seb life - n amer medelst bolag" => [
		"seb life - n amer medelst bolag",
		"seb life nordamer medelst bola"
	],
	"seb life - n america equity" => [
		"seb life - n america equity",
		"seb life fund north america eq",
		"seb life nordamer",
		"seb life nordamerika",
		"seb life nordamerikafond"
	],
	"seb life - nordenfond" => [
		"seb life - nordenfond",
		"seb life nordenfond"
	],
	"seb life - obligation flexibel" => [
		"seb life - obligation flexibel",
		"seb life obligationsfond flexi"
	],
	"seb life - optionsrätter europa" => [
		"seb life - optionsrätter europa",
		"seb life oprion europa",
		"seb life option europa",
		"seb life optionsrätter europafnd"
	],
	"seb life - sverige småbolag" => [
		"seb life - sverige småbolag",
		"seb life sverige småbolagsfond"
	],
	"seb life - swe short-med term" => [
		"seb life - swe short-med term",
		"seb life fund swe short-med term",
		"seb life räntefond",
		"seb life sv räntef",
		"seb life sverige räntefond"
	],
	"seb life - technology" => [
		"seb life - technology",
		"seb life fund technology",
		"seb life teknologi",
		"seb life teknologifond"
	],
	"seb life - wireless communicat" => [
		"seb life - wireless communicat",
		"seb life wireless communication"
	],
	"seb life - world" => [
		"seb life - world",
		"seb life fund world",
		"seb life världen",
		"seb life världenfond"
	],
	"seb life - Östeuropa" => [
		"seb life - Östeuropa",
		"seb life Östeuropa",
		"seb life Östeuropafond"
	],
	"seb likviditetsfond sek" => [
		"seb likviditetsfond sek",
		"seb likviditetsfond"
	],
	"seb likviditetsfond sek ack" => [
		"seb likviditetsfond sek ack",
		"seb likviditetsfond acc"
	],
	"seb lux cg china guaranteed" => [
		"seb lux cg china guaranteed",
		"seb a kina garanti",
		"seb a kina garantifond"
	],
	"seb lux cg emerging europe guar" => [
		"seb lux cg emerging europe guar",
		"seb a Östeuropa ga",
		"seb a Östeuropa garanti"
	],
	"seb lux cs germany fund acc" => [
		"seb lux cs germany fund acc",
		"seb a germany a",
		"seb a germany fund a",
		"seb a germany fund acc"
	],
	"seb lux cs germany fund inc" => [
		"seb lux cs germany fund inc",
		"seb a germany b",
		"seb a germany fund b",
		"seb a germany fund inc"
	],
	"seb lux cs us fund acc" => [
		"seb lux cs us fund acc",
		"seb a us a",
		"seb a us fund a",
		"seb a us fund acc",
		"seb a us-fund acc"
	],
	"seb lux cs us fund inc" => [
		"seb lux cs us fund inc",
		"seb a us b",
		"seb a us fund b",
		"seb a us fund inc",
		"seb a us-fund inc"
	],
	"seb lux fund ethical" => [
		"seb lux fund ethical",
		"sweden	seb lux (f) sverige"
	],
	"seb lux norge aksjefond" => [
		"seb lux norge aksjefond",    
		"seb skandifond norge räntef" 
	],
	"seb lång obligationsfond" => [
		"seb lång obligationsfond",
		"seb a obligation",
		"seb a obligationsfond"
	],
	"seb läkemedelsfond - lux utd" => [
		"seb läkemedelsfond - lux utd",
		"seb lux (f) läkemedel bioteknik",
		"seb lux (f) läkemedel- & biotekn",
		"seb lux fund medical",
		"seb fund läkemedel"
	],
	"seb choice nordamerikafond" => [
		"seb choice nordamerikafond",
		"seb nordamerika",
		"seb nordamerikafond"
	],
	"seb ch nordamerika c r-lux ack" => [
		"seb ch nordamerika c r-lux ack",
		"seb co nordamerika c r-lux ack",
		"seb nordamerika c r - lux ack"
	],
	"seb ch nordamerika c - lux ack" => [
		"seb ch nordamerika c - lux ack",
		"seb co nordamerika c - lux ack",
		"seb nordamerikafond c - lux ack"
	],
	"seb nordamerikafond - lux ack" => [
		"seb nordamerikafond - lux ack",
		"seb nordamerika - lux ack",
		"seb lux equity north america",
		"seb lux north america fund",
		"seb skandifond north america"
	],
	"seb ch nordamerika d - lux utd" => [
		"seb ch nordamerika d - lux utd",
		"seb co nordamerika d - lux utd",
		"seb nordamerikafond - lux utd",
		"seb nordamerika - lux utd",
		"seb lux fund north america eq",
		"seb lux (f) nordamerikafond",
		"seb fund nordamer",
		"seb fund nordamerika"
	],
	"seb nordamerikafond chans risk" => [
		"seb nordamerikafond chans/risk",
		"seb nordamerika chans risk",
		"seb nordamerika chans riskfond"
	],
	"seb choice namer medelst bolag" => [
		"seb choice namer medelst bolag",
		"seb nordam medelstora bolag",
		"seb nordamerika medelstora bol",
		"seb nordamerika medelstora bolag"
	],
	"seb choice nordamerik småbolag" => [
		"seb choice nordamerik småbolag",
		"seb nordamerikafond småbolag",
		"seb nordamerika småbolag",
		"seb nordamerikanska småbolag",
		"seb noam småbolag",
		"seb nordam småbolagsfond",
		"seb nordamerika småbolagsfond"
	],
	"seb norden småbolagsfond" => [
		"seb norden småbolagsfond",
		"seb nordiska småbolagsfond"
	],
	"seb nordenfond - lux ack" => [
		"seb nordenfond - lux ack",
		"seb lux equity fund nordic",
		"seb lux nordic fund",
		"seb skandifond nordic"
	],
	"seb oblfond eur - lux ack" => [
		"seb oblfond eur - lux ack",
		"seb lux bond fund euro acc",
		"seb lux euro bond fund acc",
		"seb skandifond bond euro acc"
	],
	"seb oblfond eur - lux utd" => [
		"seb oblfond eur - lux utd",
		"seb lux bond fund euro inc",
		"seb lux euro bond fund inc",
		"seb skandifond bond euro inc"
	],
	"seb oblfond europa - lux ack" => [
		"seb oblfond europa - lux ack",
		"seb oblfond europa usd - lux ack",
		"seb lux bond fund europe acc",
		"seb lux europe bond fund acc",
		"seb skandifond europe bond acc"
	],
	"seb oblfond flex sek - lux ack" => [
		"seb oblfond flex sek - lux ack",
		"seb lux bond sek flexible acc",
		"seb lux sek flexible bond acc",
		"seb skandifond swe flex acc"
	],
	"seb oblfond flex sek - lux utd" => [
		"seb oblfond flex sek - lux utd",
		"seb lux bond sek flexible inc",
		"seb lux sek flexible bond inc",
		"seb skandifond swe flex inc"
	],
	"seb oblfond flexibel sek" => [
		"seb oblfond flexibel sek",
		"seb avkastning"
	],
	"seb oblfond global" => [
		"seb oblfond global",
		"seb oblfond global sek",
		"seb interobligationsfond",
		"seb inter-oblfond",
		"seb inter-obligationsfond",
		"seb internationell obligation"
	],
	"seb oblfond global - lux ack" => [
		"seb oblfond global - lux ack",
		"seb oblfond global usd - lux ack",
		"seb lux bond international acc",
		"seb lux international bond acc",
		"seb skandifond bond int acc"
	],
	"seb oblfond global - lux utd" => [
		"seb oblfond global - lux utd",
		"seb oblfond global usd - lux utd",
		"seb lux bond international inc",
		"seb lux international bond inc",
		"seb skandifond bond int inc",
		"seb skandifond int income"
	],
	"seb oblfond sek - lux ack" => [
		"seb oblfond sek - lux ack",
		"seb lux bond fund sek acc",
		"seb lux sek bond fund acc",
		"seb skandifond sweden bond acc"
	],
	"seb oblfond sek - lux utd" => [
		"seb oblfond sek - lux utd",
		"seb lux bond fund sek inc",
		"seb lux sek bond fund inc",
		"seb skandifond sweden bond inc"
	],
	"seb oblfond usd - lux ack" => [
		"seb oblfond usd - lux ack",
		"seb lux bond fund usd acc",
		"seb lux usd short bond fund",
		"seb skandifond short bond usd"
	],
	"seb oblfond usd - lux utd" => [
		"seb oblfond usd - lux utd",
		"seb lux bond fund usd inc",
		"seb lux usd bond fund inc",
		"seb skandifond dollar bond inc"
	],
	"seb obligationsfond sek" => [
		"seb obligationsfond sek",
		"seb oblfond sek",
		"seb obligationsfon",
		"seb obligationsfond",
		"seb obligationsfond 1"
	],
	"seb obligationsfond 2" => [
		"seb obligationsfond 2",
		"seb trygg obligation",
		"trygg obligatfond",
		"trygg obligationsfond"
	],
	"seb offensiv placeringsfond" => [
		"seb offensiv placeringsfond",
		"seb trygg offensiv placering",
		"trygg offensiv",
		"trygg offensiv placeringsfond"
	],
	"seb optionsrätter eur - lux ack" => [
		"seb optionsrätter eur - lux ack",
		"seb lux equity opportun europe"
	],
	"seb optionsrätter europa" => [
		"seb optionsrätter europa",
		"seb optionsrätter europafond",
		"trygg optionsrätter europafond"
	],
	"seb pb portfölj balanserad" => [
		"seb pb portfölj balanserad",
		"seb eb balanserad portfölj",
		"eb portfölj balanserad",
		"seb modellportfölj"
	],
	"seb pb europeisk aktieportfölj" => [
		"seb pb europeisk aktieportfölj",
		"seb eb europeisk aktieportfölj",
		"eb europeisk aktieportfölj",
		"seb europeisk aktieportfölj"
	],
	"seb pb portfölj försiktig" => [
		"seb pb portfölj försiktig",
		"seb eb portfölj försiktig",
		"eb portfölj försiktig",
		"seb portfölj försiktig"
	],
	"seb pb portfölj möjlighet" => [
		"seb pb portfölj möjlighet",
		"seb eb portfölj möjlighet",
		"eb portfölj möjlighet",
		"seb portfölj möjlighet"
	],
	"seb pb svensk aktieportfölj" => [
		"seb pb svensk aktieportfölj",
		"seb eb svensk aktieportfölj",
		"eb svensk aktieportfölj",
		"seb svensk aktieportfölj"
	],
	"seb penningmark eur - lux ack" => [
		"seb penningmark eur - lux ack",
		"seb lux short bond fund (eur)",
		"seb lux short bond fund euro",
		"seb lux euro short bond fund",
		"seb short bo euro",
		"seb skandifond short bond euro"
	],
	"seb penningmark nok - lux ack" => [
		"seb penningmark nok - lux ack",
		"seb norge rente nok - lux ack",
		"seb lux norge rentefond",
		"seb skandifond norge"
	],
	"seb penningmark sek - lux ack" => [
		"seb penningmark sek - lux ack",
		"seb lux short bond fund (sek)",
		"seb lux short bond fund sek",
		"seb lux sek short bond fund",
		"seb short bond sek",
		"seb skandifond short bond sek"
	],
	"seb penningmark sek 2 - lux utd" => [
		"seb penningmark sek 2 - lux utd",
		"seb lux fund swe short-med term",
		"seb lux fund swedish medium term",
		"seb lux (f) avkastningsfond",
		"seb fund avkastnf",
		"seb fund avkastningsfond"
	],
	"seb penningmark usd - lux ack" => [
		"seb penningmark usd - lux ack",
		"seb skandifond dollar bond acc",
		"seb lux short bond fund (usd)",
		"seb lux short bond fund usd",
		"seb lux usd bond fund acc"
	],
	"seb penningmarknad global" => [
		"seb penningmarknad global",
		"seb penningmark global",
		"seb penningmark global sek",
		"seb inter - penningmarknad",
		"seb inter-penningmarknfond",
		"seb internationell penningmark",
		"seb interpenningmarknadsfond",
		"sebinter-pennmfond"
	],
	"seb penningmarknadsfond sek" => [
		"seb penningmarknadsfond sek",
		"seb penningmark sek",
		"seb penningmarknad",
		"seb penningmarknadsfond"
	],
	"seb realräntefond sek - lux utd" => [
		"seb realräntefond sek - lux utd",
		"seb lux fund i l bond realränta"
	],
	"seb rysslandfond lux ack" => [
		"seb rysslandfond lux ack",
		"seb rysslandfond - lux ack",
		"seb rysslandsfond - lux ack",
	],
	"seb råvarufond - lux ack" => [
		"seb råvarufond - lux ack",
		"seb lux equity natural resources",
		"seb lux natural resources fund",
		"seb skandifond natural resour"
	],
	"seb småbolag" => [
		"seb småbolag",
		"seb småbolagsfond",
		"seb småbolagsfonden"
	],
	"seb stiftelsefond obligation sek" => [
		"seb stiftelsefond obligation sek",
		"seb stiftelsefond obligation"
	],
	"seb stiftelsefond sverige" => [
		"seb stiftelsefond sverige",
		"seb stiftelse sve"
	],
	"seb stiftelsefond utland" => [
		"seb stiftelse utl",
		"seb stiftelse utland",
		"seb stiftelsefond utland"
	],
	"seb sverige offensivfond" => [
		"seb sverige offensivfond",
		"seb a likviditet",
		"seb a likviditetsfond"
	],
	"seb sverige småbolag chans risk" => [
		"seb sverige småbolag chans risk",
		"seb allemansfond chans risk"
	],
	"seb sverigefond chans risk" => [
		"seb sverigefond chans risk",
		"seb sverige chans risk",
		"seb sverige chans riskfond",
		"seb fund sverige räntefond"
	],
	"seb sverigefond i" => [
		"seb sverigefond i",
		"seb sverige i",
		"seb sverige aktiefond i",
		"seb sverigefond 1",
		"seb allemansfond sverige 1"
	],
	"seb sverigefond ii" => [
		"seb sverigefond ii",
		"seb sverige ii",
		"seb sverige aktiefond ii",
		"seb sverigefond 2",
		"seb allemansfond sverige 2"
	],
	"seb sverigefond småbolag" => [
		"seb sverigefond småbolag",
		"seb sverige småbolag",
		"seb sverige småbolagsfond"
	],
	"seb teknologifond - lux utd" => [
		"seb teknologifond - lux utd",
		"seb lux fund technology",
		"seb lux (f) teknologifond",
		"seb fund teknologi"
	],
	"seb trygg f&c latin america" => [
		"seb trygg f&c latin america",
		"trygg f&c latin america",
		"trygg f&c latin american (sek)",
		"trygg f&c latina"
	],
	"seb trygg flem eastern europe" => [
		"seb trygg flem eastern europe",
		"trygg flem easteur",
		"trygg emerging markets fond",
		"trygg emerging markets fund",
		"trygg emerging marketsfond",
		"trygg fleming east european(sek)",
		"trygg fleming eastern european"
	],
	"seb trygg flem european small co" => [
		"seb trygg flem european small co",
		"trygg flemeurosmal",
		"trygg fleming eurosmall (sek)",
		"trygg fleming eurosmallcomp"
	],
	"seb trygg läkemedelsfond" => [
		"seb trygg läkemedelsfond",
		"trygg läkemedelsf",
		"trygg läkemedelsfond"
	],
	"seb trygg placeringsfond" => [
		"seb trygg placeringsfond",
		"trygg placeringsf",
		"trygg placeringsfond"
	],
	"seb trygg schroder jap small co" => [
		"seb trygg schroder jap small co",
		"trygg schroder japan small (sek)",
		"trygg schroder japan smaller"
	],
	"seb trygg schroder uk equity" => [
		"seb trygg schroder uk equity",
		"trygg schroder uk equity",
		"trygg schroder uk equity (sek)"
	],
	"seb trygg schroder us smaller co" => [
		"seb trygg schroder us smaller co",
		"trygg schroder us small (sek)",
		"trygg schroder us smaller comp",
	],
	"seb trygg scottish cash" => [
		"seb trygg scottish cash",
		"seb trygg scottish eq cash",
		"trygg scottish equitable cash",
		"trygg scottish eq cash",
		"trygg scottish equitable cash"
	],
	"seb trygg scottish eq american" => [
		"seb trygg scottish eq american",
		"trygg scottish eq american"
	],
	"seb trygg scottish eq europe" => [
		"seb trygg scottish eq europe",
		"trygg scottish eq europe"
	],
	"seb trygg scottish eq far east" => [
		"seb trygg scottish eq far east",
		"trygg scottish eq far east",
		"trygg scottish equitable far eas"
	],
	"seb trygg scottish eq mixed" => [
		"seb trygg scottish eq mixed",
		"trygg scottish eq mixed",
		"trygg scottish equitable mixed"
	],
	"seb trygg scottish equity bond" => [
		"seb trygg scottish equity bond",
		"trygg scottish equity bond",
		"seb trygg scottish europe bond"
	],
	"seb trygghetsfond ekorren" => [
		"seb trygghetsfond ekorren",
		"seb ekorren trygghetsfond",
		"trygg småbolagsfo",
		"trygg småbolagsfond"
	],
	"seb tysklandsfond" => [
		"seb tysklandsfond",
		"seb a tyskland",
		"seb a tysklandsfond"
	],
	"seb världen" => [
		"seb världen",
		"seb världenfond"
	],
	"seb världenfond - lux utd" => [
		"seb världenfond - lux utd",
		"seb lux fund world",
		"seb lux (f) världenfond",
		"seb fund världen"
	],
	"seb wirelessfond - lux ack" => [
		"seb wirelessfond - lux ack",
		"seb lux eq wireless communicat"
	],
	"seb Östersjöfond wwf" => [
		"seb Östersjöfond wwf",
		"seb Östersjö wwf"
	],
	"seb Östeuropa" => [
		"seb Östeuropa",
		"seb Östeuropafond"
	],
	"seb Östeurfond småbo - lux ack" => [
		"seb Östeurfond småbo - lux ack",
		"seb Östeuropafond - lux ack",
		"seb Östeuropa - lux ack",
		"seb lux eastern europe fund",
		"seb skandifond eastern europe"
	],
	"seb Östeurfondxryssland- lux ack" => [
		"seb Östeurfondxryssland- lux ack",
		"seb baltikumfond - lux ack",
	],
	"trowe price us l-cap grow eq a" => [
		"trowe price us l-cap grow eq a",
		"t-rowe us large cap gr eq a"
	],
	"trygg asienfond" => [
		"trygg asienfond",
		"trygg fri placering asien"
	],
	"trygg europa" => [
		"trygg europa",
		"trygg europa fond",
		"trygg europafond"
	],
	"trygg japan fond" => [
		"trygg japan fond",
		"trygg japanfond"
	],
	"trygg nordamerika" => [
		"trygg nordamerika",
		"trygg nordamerika fond",
		"trygg nordamerikafond"
	],
	"trygg sverige" => [
		"trygg sverige",
		"trygg sverigefond"
	]
);

#
# The funds in these two lists (i.e. "full_list" and "exist_nonfull_list")
# are printed in the output.
#
# Fund names must be in lower case
# v-v-v-v-v-v-v-v-v-v-v-v-v-v-v-v-v-
# Funds that have disappeared
#	"alterum global quality growth",
#	"seb nordamerikafond chans risk",
#	"seb nordamerikafond - lux ack",
#	"seb forskningsfond sv läk sällsk",
#	"seb hedgefond",
#	"seb råvarufond",
#	"seb råvarufond - lux ack",
#	"seb oblfond europa - lux ack",
#	"seb oblfond global",
#	"seb oblfond global - lux ack",
#	"seb oblfond global - lux utd",
#	"seb oblfond usd - lux ack",
#	"seb oblfond usd - lux utd",
#	"seb penningmarknad global",
# ^-^-^-^-^-^-^-^-^-^-^-^-^-^-^-^-^-
@full_list = (
	"blackrock japan opportunitie",
	"fidelity asian special",
	"jf china fund a",
	"seb aktiespar",
	"seb alpha bond sek d - lux utd",
	"seb ch asien små x j - lux ack",
	"seb choice asienfond ex japan",
	"seb ch asien x jap - lux ack",
	"seb ch asien x jap - lux utd",
	"seb cancerfond",
	"seb choice emerging markets",
	"seb ch emerging mark - lux ack",
	"seb etisk europafond - lux ack",
	"seb etisk globalfond - lux utd",
	"seb etisk globalfond",
	"seb etisk sverigefond - lux utd",
	"seb europa",
	"seb europa chans risk - lux ack",
	"seb europafond - lux utd",
	"seb europafond 1 - lux ack",
	"seb europafond 2 - lux ack",
	"seb europafond 3 - lux ack",
	"seb europafond småbolag",
	"seb fastighetsfond",
	"seb global",
	"seb globalfond - lux ack",
	"seb globalfond - lux utd",
	"seb internat blandfond - lux ack",
	"seb internat blandfond - lux utd",
	"seb internet",
	"seb choice japanfond",
	"seb ch japanfond c - lux ack",
	"seb ch japanfond d - lux utd",
	"seb choice latinamerika",
	"seb life - asia equity",
	"seb life - ethical global",
	"seb life - ethical sweden",
	"seb life - europe equity",
	"seb life - global equity",
	"seb life - index linked bond",
	"seb life - japan equity",
	"seb life - latinamerikafond",
	"seb life - medical",
	"seb life - n america equity",
	"seb life - swe short-med term",
	"seb life - technology",
	"seb life - world",
	"seb likviditetsfond sek",
	"seb läkemedelsfond - lux utd",
	"seb läkemedelsfond",
	"seb choice nordamerikafond",
	"seb ch nordamerika c - lux ack",
	"seb ch nordamerika d - lux utd",
	"seb choice nordamerik småbolag",
	"seb nordenfond",
	"seb nordenfond - lux ack",
	"seb oblfond eur - lux ack",
	"seb oblfond eur - lux utd",
	"seb oblfond europa - lux utd",
	"seb oblfond flex sek - lux ack",
	"seb oblfond flex sek - lux utd",
	"seb oblfond flexibel sek",
	"seb oblfond sek - lux ack",
	"seb oblfond sek - lux utd",
	"seb obligationsfond sek",
	"seb penningmark eur - lux ack",
	"seb penningmark nok - lux ack",
	"seb penningmark sek - lux ack",
	"seb penningmark sek 2 - lux utd",
	"seb penningmark usd - lux ack",
	"seb penningmarknadsfond sek",
	"seb schweizfond",
	"seb stiftelsefond obligation sek",
	"seb stiftelsefond sverige",
	"seb stiftelsefond utland",
	"seb sverige småbolag chans risk",
	"seb sverigefond chans risk",
	"seb sverigefond i",
	"seb sverigefond ii",
	"seb sverigefond småbolag",
	"seb teknologifond",
	"seb teknologifond - lux utd",
	"seb trygg placeringsfond",
	"seb trygg scottish cash",
	"seb trygg scottish eq american",
	"seb trygg scottish eq europe",
	"seb trygg scottish eq far east",
	"seb trygg scottish eq mixed",
	"seb trygg scottish equity bond",
	"seb trygghetsfond ekorren",
	"seb världen",
	"seb världenfond - lux utd",
	"seb Östersjöfond wwf",
	"seb Östeurfondxryssland- lux ack",
	"seb Östeuropa",
	"seb Östeurfond småbo - lux ack"
);

# v-v-v-v-v-v-v-v-v-v-v-v-v-v-v-v-v-
# Funds that have disappeared
#	"baring north america",
#	"goldman gl consumer grow",
#	"goldman sachs brics portfolio",
#	"seb bioteknikfond - lux ack",
#	"seb optionsrätter eur - lux ack",
#	"seb premiefond 50",
#	"seb premiefond 55",
#	"seb premiefond 60",
#	"seb premiefond 65",
#	"seb premiefond 70",
#	"seb premiefond 75",
# ^-^-^-^-^-^-^-^-^-^-^-^-^-^-^-^-^-
@exist_nonfull_list = (
	'ab american growth a $',
	'ab american value a $',
	'ab international tech fund a $',
	'ab global growth trends a $',
	"abn amro amerika",
	'acm global inv american val a$',
	"alfred berg amerika",
	"alliance capital american growth",
	"alliance capital glob grow trend",
	"alliance capital int technology",
	"alliancebernstein amer val a usd",
	"banco amerika",
	"blackrock european",
	"blackrock global equity",
	"blackrock global opportun",
	"blackrock global small cap p",
	"blackrock latin america a2",
	"carnegie east european",
	"east capital balkanfonden",
	"east capital ryssland",
	"east capital turkietfonden",
	'eaton emerald us value fund a2$',
	"eaton vance emerald us value a2",
	"fidelity euro growth",
	"fidelity euro small",
	"fidelity international",
	"gartmore gl focus fund",
	"goldman brics portfol eur e cap",
	"goldman europe core flx eq ptf",
	"goldman gl financial services",
	"goldman sachs global eq",
	"goldman sachs global high yield",
	"hsbc indian equity",
	"hsbc brazil equity",
	"jf pacific equity a",
	"jpm gbl natural resources a acc",
	"pictet biotech p",
	"schroder emerging europe a acc",
	"schroder emerging mkt debt a acc",
	"seb alpha bond sek a inst",
	"seb alpha bond sek b inst",
	"seb alpha bond sek c - lux ack",
	"seb alpha sh bond sek a inst",
	"seb alpha sh bond sek b inst",
	"seb alpha sh bond sek c-lux ack",
	"seb alpha sh bond sek d-lux utd",
	"seb asset selection sek-lux ack",
	"seb bioteknikfond - lux utd",
	"seb choice sverigefond 1",
	"seb choice sverigefond 2",
	"seb currency alpha sek-lux ack",
	"seb ethos aktiefond",
	"seb ethos räntefond",
	"seb corporate bond eur - lux ack",
	"seb corporate bond eur - lux utd",
	"seb corporate bond sek - lux ack",
	"seb corporate bond sek - lux utd",
	"seb europa småbolag - lux utd",
	"seb europeisk aktieportfölj",
	"seb fond i fond balanserad",
	"seb fond i fond global",
	"seb företagsoblfond sek ack",
	"seb garantifond 80",
	"seb generationsfond 50-tal",
	"seb generationsfond 60-tal",
	"seb generationsfond 70-tal",
	"seb generation fund 80",
	"seb global chans risk - lux ack",
	"seb global eq l s sek - luxack",
	"seb global hedge - lux ack",
	"seb guarantee fund 80",
	"seb ch global value - lux ack",
	"seb ch global value - lux utd",
	"seb ch japan c r - lux ack",
	"seb life - emerging markets",
	"seb life - europa småbolag",
	"seb life - internet",
	"seb life - n amer medelst bolag",
	"seb life - nordenfond",
	"seb life - obligation flexibel",
	"seb life - optionsrätter europa",
	"seb life - sverige småbolag",
	"seb life - wireless communicat",
	"seb life - Östeuropa",
	"seb likviditetsfond sek ack",
	"seb modellportfölj",
	"seb multihedge",
	"seb choice namer medelst bolag",
	"seb ch nordamerika c r-lux ack",
	"seb nordic eq l s sek-lux ack",
	"seb oblfond flexibel sek",
	"seb optionsrätter europa",
	"seb pb europeisk aktieportfölj",
	"seb pb portfölj balanserad",
	"seb pb portfölj försiktig",
	"seb pb portfölj möjlighet",
	"seb pb svensk aktieportfölj",
	"seb realräntefond sek - lux utd",
	"seb rysslandfond lux ack",
	"seb räntehedge alpha",
	"seb special clients fif global",
	"seb special clients sverige",
	"seb stiftelsefond balanserad",
	"seb svensk aktieportfölj",
	"seb swedish focus fund",
	"seb swedish value fund",
	"seb wirelessfond - lux ack",
	"selector global value a1",
	"skf allemansfond",
	"trowe price us l-cap grow eq a"
);
