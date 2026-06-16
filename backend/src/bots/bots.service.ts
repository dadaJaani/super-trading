import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Bot } from '../entities/bot.entity';

@Injectable()
export class BotsService {
  constructor(
    @InjectRepository(Bot)
    private readonly botsRepository: Repository<Bot>,
  ) {}

  findAll(): Promise<Bot[]> {
    return this.botsRepository.find({ order: { createdAt: 'DESC' } });
  }

  findOne(id: string): Promise<Bot | null> {
    return this.botsRepository.findOne({ where: { id } });
  }
}
