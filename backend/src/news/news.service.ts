import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { News } from '../entities/news.entity';

@Injectable()
export class NewsService {
  constructor(
    @InjectRepository(News)
    private readonly newsRepository: Repository<News>,
  ) {}

  findRecent(limit = 50): Promise<News[]> {
    return this.newsRepository.find({
      order: { time: 'DESC' },
      take: limit,
    });
  }
}
