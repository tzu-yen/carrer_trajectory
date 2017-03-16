create table profile.education
(
	id				serial primary key,
	profile_id			int REFERENCES search.person_linkedin_profile(id) ON DELETE CASCADE,
	school				varchar(200),
	field				varchar(200),
	degree				varchar(200),
	start_year			int,
	end_year			int,
	create_time			timestamp default now(),
	update_time			timestamp
);
create index education_school_lower_idx on profile.education(lower(school));
create index education_field_lower_idx on profile.education(lower(field));
create index education_degree_lower_idx on profile.education(lower(degree));