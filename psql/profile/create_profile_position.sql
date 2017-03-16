create table profile.position
(
	id					serial primary key,
	profile_id 			int REFERENCES search.person_linkedin_profile(id) ON DELETE CASCADE,
	title				varchar(200),
	company				varchar(500),
	start_year			int,
	end_year			int,
	is_current			boolean default false,
	create_time			timestamp default now(),
	update_time			timestamp
);
create index position_title_lower_idx on profile.position(lower(title));
create index position_company_lower_idx on profile.position(lower(company));
