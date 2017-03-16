create table profile.person
(
	id 						serial primary key,
	rid						int REFERENCES search.person_linkedin_profile(id) ON DELETE CASCADE,
	lnkd_url				varchar(2083) unique not null,
	name					varchar(400),
	location				varchar(100),
	industry				varchar(100),
	connections				int,
	picture_id				varchar(50),
	email					varchar(254),
	summary					text,
	create_time				timestamp default now(),
	update_time				timestamp
);
create index person_name_lower_idx on profile.person(lower(name));
create index person_email_lower_idx on profile.person(lower(email));
create index person_lnkd_url_idx on profile.person(lnkd_url);
create index person_location_lower_idx on profile.person(lower(location));
create index person_industry_lower_idx on profile.person(lower(industry));