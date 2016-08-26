DROP TABLE IF EXISTS `hagroup`;
CREATE TABLE `f5cluster` (
 `ID` int(10) unsigned NOT NULL auto_increment,
 `name` varchar(32) NOT NULL,
 `description` varchar(32) NOT NULL,
 `active_id` int(10) unsigned NOT NULL,
 PRIMARY KEY (`ID`)
);


DROP TABLE IF EXISTS `ltm`;
CREATE TABLE `bigip` (
 `ID` int(10) unsigned NOT NULL auto_increment,
 `name` varchar(128) NOT NULL,
 `version` varchar(16) NOT NULL,
 `hagroup_id` int(10) unsigned NOT NULL,
 PRIMARY KEY (`ID`)
);


DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
 `ID` int(10) unsigned NOT NULL auto_increment,
 `username` varchar(128) NOT NULL,
 PRIMARY KEY (`ID`)
);


DROP TABLE IF EXISTS `vs`;
CREATE TABLE `vs` (
 `ID` int(10) unsigned NOT NULL auto_increment,
 `name` varchar(128) NOT NULL,
 `hagroup_ID` int(10) unsigned NOT NULL,
 PRIMARY KEY (`ID`)
);

DROP TABLE IF EXISTS `users_vs`;
CREATE TABLE `users_vs` (
 `users_ID` int(10) unsigned NOT NULL,
 `vs_ID` int(10) unsigned NOT NULL
);

CREATE TABLE `pools` (
 `ID` int(10) unsigned NOT NULL auto_increment,
 `name` varchar(128) NOT NULL,
 `hagroup_ID` int(10) unsigned NOT NULL,
 PRIMARY KEY (`ID`)
);

DROP TABLE IF EXISTS `groups_pools`;
CREATE TABLE `groups_pool` (
 `groups_ID` int(10) unsigned NOT NULL,
 `pools_ID` int(10) unsigned NOT NULL
);

DROP TABLE IF EXISTS `groups`;
CREATE TABLE `groups` (
 `ID` int(10) unsigned NOT NULL auto_increment,
 `groupname` varchar(128) NOT NULL,
 PRIMARY KEY (`ID`)
);

DROP TABLE IF EXISTS `users_groups`;
CREATE TABLE `users_groups` (
 `users_ID` int(10) unsigned NOT NULL,
 `groups_ID` int(10) unsigned NOT NULL
);


DROP TABLE IF EXISTS `users_pools`;
CREATE TABLE `users_pools` (
 `users_ID` int(10) unsigned NOT NULL,
 `pools_ID` int(10) unsigned NOT NULL
);

INSERT INTO `groups` values (1, 'administrator');
INSERT INTO `groups` values (2, 'kevin.coming');

INSERT INTO `users_groups` values (1,1);
INSERT INTO `users_groups` values (1,2);
