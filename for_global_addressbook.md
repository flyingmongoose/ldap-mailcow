БД prefix должен быть **roundcube_**

В roundcube устанавливаем plugin https://github.com/johndoh/roundcube-globaladdressbook

Создаем хотя бы одну запись в новой глобальной адресной книге и смотрим в таблице roundcube_contacts user_id пользователя глобальной адресной книги. В SQL коде ниже это значение 5. Меняем на свое.

Создаем в БД view:
```sql
CREATE
    ALGORITHM = UNDEFINED
    DEFINER = `mailcow@%`
    SQL SECURITY DEFINER
VIEW `roundcube_contacts_view` AS
SELECT
  SUBSTRING(CONV(SUBSTRING(CAST(SHA(CONCAT(`mailcow`.`mailbox`.`name`, ',', `mailcow`.`mailbox`.`username`)) AS CHAR), 1, 16), 16, 10),1,5) as 'contact_id',
  `mailcow`.`mailbox`.`modified` AS `changed`,
  0 as `del`,
      `mailcow`.`mailbox`.`name` AS `name`,
      `mailcow`.`mailbox`.`username` AS `email`,
  `mailcow`.`mailbox`.`name` AS `firstname`,
  '' AS `surname`,
  '' AS `vcard`,
  concat(`mailcow`.`mailbox`.`name`, ' ', `mailcow`.`mailbox`.`username`) as `words`,
  5 as `user_id`
  FROM `mailcow`.`mailbox` where `mailcow`.`mailbox`.`active`=1
Union all
SELECT
  SUBSTRING(CONV(SUBSTRING(CAST(SHA(CONCAT(`mailcow`.`alias`.`address`, ',', `mailcow`.`alias`.`goto`)) AS CHAR), 1, 16), 16, 10),1,5) as 'contact_id',
  `mailcow`.`alias`.`modified` AS `changed`,
  0 as `del`,
  `mailcow`.`alias`.`address` AS `name`,
  `mailcow`.`alias`.`goto` as `email`,
  `mailcow`.`alias`.`address` AS `firstname`,
  '' AS `surname`,
  '' AS `vcard`,
  `mailcow`.`alias`.`address` as `words`,
  5 as `user_id`
  FROM `mailcow`.`alias` WHERE `mailcow`.`alias`.`address` != `mailcow`.`alias`.`goto` and `mailcow`.`alias`.`active`=1
  ```
  Создаем процедуру:
  ```sql
CREATE DEFINER=`mailcow`@`%` PROCEDURE `sync_contacts_with_view`()
LANGUAGE SQL
NOT DETERMINISTIC
CONTAINS SQL
SQL SECURITY DEFINER
COMMENT ''
BEGIN

INSERT INTO roundcube_contacts(user_id, changed, del, name, email, firstname, surname, vcard, words)
SELECT user_id, changed, del, name, email, firstname, surname, vcard, words
FROM roundcube_contacts_view WHERE NOT EXISTS (SELECT 1 FROM roundcube_contacts WHERE binary roundcube_contacts.words = binary roundcube_contacts_view.words and roundcube_contacts_view.user_id=5);

UPDATE roundcube_contacts AS M LEFT JOIN roundcube_contacts_view AS N ON binary M.words = binary N.words
	SET M.changed=N.changed,
	M.del=N.del,
	M.name=N.name,
	M.email=N.email,
	M.firstname=N.firstname,
	M.surname=N.surname,
	M.vcard=N.vcard,
	M.words=N.words
WHERE N.user_id=5 and binary M.words=binary N.words;

DELETE
FROM    roundcube_contacts
WHERE   user_id=5 and words NOT IN (SELECT binary words FROM roundcube_contacts_view);

END;
  ```
Создаем триггеры для таблиц alias и mailbox:
```sql
CREATE DEFINER=`mailcow`@`%` TRIGGER `alias_after_insert` AFTER INSERT ON `alias` FOR EACH ROW BEGIN
CALL `sync_contacts_with_view`();
END;
CREATE DEFINER=`mailcow`@`%` TRIGGER `alias_after_update` AFTER UPDATE ON `alias` FOR EACH ROW BEGIN
CALL `sync_contacts_with_view`();
END;
CREATE DEFINER=`mailcow`@`%` TRIGGER `alias_after_delete` AFTER DELETE ON `alias` FOR EACH ROW BEGIN
CALL `sync_contacts_with_view`();
END;
CREATE DEFINER=`mailcow`@`%` TRIGGER `mailbox_after_insert` AFTER INSERT ON `mailbox` FOR EACH ROW BEGIN
CALL `sync_contacts_with_view`();
END;
CREATE DEFINER=`mailcow`@`%` TRIGGER `mailbox_after_update` AFTER UPDATE ON `mailbox` FOR EACH ROW BEGIN
CALL `sync_contacts_with_view`();
END;
CREATE DEFINER=`mailcow`@`%` TRIGGER `mailbox_after_delete` AFTER DELETE ON `mailbox` FOR EACH ROW BEGIN
CALL `sync_contacts_with_view`();
END;
```
Тестируем и радуемся.
